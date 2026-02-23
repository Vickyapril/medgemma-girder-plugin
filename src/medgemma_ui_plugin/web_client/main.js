import { wrap } from '@girder/core/utilities/PluginUtils';
import ItemView from '@girder/core/views/body/ItemView';
import { restRequest } from '@girder/core/rest';
import events from '@girder/core/events';

const ACTION_CLASS = 'g-run-dicom-pipeline-action';
const STATUS_ID = 'g-run-dicom-pipeline-status';
const PROGRESS_ID = 'g-run-dicom-pipeline-progress';
const POLL_MS = 3000;
const MAX_STATUS_RETRIES = 30;

function setProgress(view, percent, label) {
    const clamped = Math.max(0, Math.min(100, Number(percent) || 0));
    const progressEl = view.$(`#${PROGRESS_ID}`);
    if (!progressEl.length) {
        return;
    }
    progressEl.find('.g-progress-inner').css('width', `${clamped}%`);
    progressEl.find('.g-progress-label').text(label || `${clamped}%`);
}

function pollRunStatus(view, runId, tokenHeader, dagId) {
    if (!runId) {
        return;
    }
    const statusEl = view.$(`#${STATUS_ID}`);
    const actionEl = view.$(`.${ACTION_CLASS}`);
    let retryCount = 0;

    const poll = () => {
        restRequest({
            method: 'GET',
            url: `medgemma/zip-status/${runId}`,
            headers: tokenHeader
        }).done((resp) => {
            retryCount = 0;
            const status = resp.status || 'unknown';
            const progress = resp.progress || {};
            const pct = progress.percent || (status === 'success' ? 100 : 0);
            setProgress(view, pct, `${status.toUpperCase()} - ${pct}%`);
            const dagLabel = dagId || resp.dag_id || 'unknown_dag';
            statusEl.text(`DAG ${dagLabel} | Run ${runId}: ${status}`);

            if (status === 'success') {
                actionEl.removeClass('disabled');
                events.trigger('g:alert', {
                    icon: 'ok',
                    text: 'DICOM pipeline completed successfully.',
                    type: 'success',
                    timeout: 6000
                });
                return;
            }
            if (status === 'failed') {
                actionEl.removeClass('disabled');
                events.trigger('g:alert', {
                    icon: 'cancel',
                    text: 'DICOM pipeline failed. Check Airflow logs.',
                    type: 'danger',
                    timeout: 8000
                });
                return;
            }
            window.setTimeout(poll, POLL_MS);
        }).fail(() => {
            retryCount += 1;
            const waitLabel = `Waiting for status (${retryCount}/${MAX_STATUS_RETRIES})`;
            statusEl.text(`Run ${runId}: status check retrying`);
            setProgress(view, 10, waitLabel);
            if (retryCount >= MAX_STATUS_RETRIES) {
                actionEl.removeClass('disabled');
                statusEl.text(`Run ${runId}: status unavailable`);
                setProgress(view, 0, 'Status unavailable');
                return;
            }
            window.setTimeout(poll, POLL_MS);
        });
    };

    window.setTimeout(poll, POLL_MS);
}

function appendPipelineButton(view) {
    if (view.$(`.${ACTION_CLASS}`).length) {
        return;
    }

    const actionHtml = `
        <li role="presentation">
            <a class="${ACTION_CLASS}" role="menuitem" href="#">
               ⚙ Run MedGemma Tirage
            </a>
        </li>
    `;

    const target = view.$('.g-item-actions-menu').first();
    if (target.length) {
        target.prepend(actionHtml);
    }

    if (!view.$(`#${STATUS_ID}`).length) {
        view.$('.g-item-header').append(
            `<div id="${STATUS_ID}" style="margin-top: 6px; font-size: 12px;"></div>`
        );
    }
    if (!view.$(`#${PROGRESS_ID}`).length) {
        view.$('.g-item-header').append(
            `<div id="${PROGRESS_ID}" style="margin-top: 6px; max-width: 380px;">
                <div style="width: 100%; background: #e9ecef; border-radius: 4px; overflow: hidden;">
                    <div class="g-progress-inner" style="width: 0%; height: 10px; background: #3c8dbc;"></div>
                </div>
                <div class="g-progress-label" style="font-size: 11px; margin-top: 4px;">Idle</div>
            </div>`
        );
    }
}

wrap(ItemView, 'render', function (render) {
    this.once('g:rendered', () => {
        appendPipelineButton(this);
    });
    return render.call(this);
});

ItemView.prototype.events[`click .${ACTION_CLASS}`] = function (event) {
    if (event && event.preventDefault) {
        event.preventDefault();
    }

    const itemId = this.model.id;
    const statusEl = this.$(`#${STATUS_ID}`);
    const actionEl = this.$(`.${ACTION_CLASS}`);
    const token = window.girder && window.girder.currentToken;
    const tokenHeader = token ? { 'Girder-Token': token } : undefined;

    statusEl.text('Starting...');
    actionEl.addClass('disabled');
    setProgress(this, 5, 'Queued');

    restRequest({
        method: 'POST',
        url: `medgemma/trigger-zip/${itemId}`
    }).done((resp) => {
        if (resp.status === 'already_processed') {
            statusEl.text('Already processed');
            setProgress(this, 100, 'Already processed');
            actionEl.removeClass('disabled');
            events.trigger('g:alert', {
                icon: 'info',
                text: resp.warning || 'Image is already processed.',
                type: 'warning',
                timeout: 7000
            });
            return;
        }
        if (resp.status === 'in_progress') {
            const existingRun = resp.job_id || 'unknown';
            statusEl.text(`Already running (${existingRun})`);
            setProgress(this, 35, 'Running');
            pollRunStatus(this, resp.job_id, tokenHeader, resp.dag_id);
            return;
        }

        const runId = resp.job_id || '';
        const dagId = resp.dag_id || 'unknown_dag';
        statusEl.text(`Started (${dagId} / ${runId || 'unknown'})`);
        setProgress(this, 10, 'Started');
        events.trigger('g:alert', {
            icon: 'ok',
            text: `DICOM pipeline started. DAG: ${dagId}, Run ID: ${runId}`,
            type: 'success',
            timeout: 8000
        });
        pollRunStatus(this, runId, tokenHeader, dagId);
    }).fail((err) => {
        const responseJson = err && err.responseJSON ? err.responseJSON : {};
        const msg = responseJson.message || responseJson.error || 'Failed to start pipeline';
        statusEl.text('Failed to start');
        setProgress(this, 0, 'Failed to start');
        events.trigger('g:alert', {
            icon: 'cancel',
            text: msg,
            type: 'danger',
            timeout: 10000
        });
    }).always(() => {
        // On success we keep disabled until polling reaches terminal state.
        if (!statusEl.text().includes('Run ') && !statusEl.text().includes('running')) {
            actionEl.removeClass('disabled');
        }
    });
};
