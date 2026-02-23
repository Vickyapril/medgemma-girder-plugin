"""Girder plugin API for MedGemma + Airflow pipeline integration."""

import cherrypy
from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource
from girder.constants import AccessType
from girder.plugin import GirderPlugin
from girder.models.item import Item

from airflow_integration import AirflowClient
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path


class MedGemmaResource(Resource):
    """Girder plugin for MedGemma analysis"""

    def __init__(self):
        super().__init__()
        self.resourceName = 'medgemma'

        self.route('POST', ('analyze', ':id'), self.analyze_item)
        self.route('POST', ('trigger-zip', ':id'), self.trigger_zip_pipeline)
        self.route('GET', ('status', ':job_id'), self.get_job_status)
        self.route('GET', ('zip-status', ':job_id'), self.get_zip_job_status)
        self.route('GET', ('item-status', ':id'), self.get_item_pipeline_status)

        # Initialize Airflow client
        airflow_url = os.getenv('AIRFLOW_URL', 'http://localhost:8080')
        airflow_user = os.getenv('AIRFLOW_USER', 'admin')
        airflow_pass = os.getenv('AIRFLOW_PASSWORD', 'admin')
        airflow_token = os.getenv('AIRFLOW_API_TOKEN')
        airflow_timeout = int(os.getenv('AIRFLOW_REQUEST_TIMEOUT', '30'))
        self.airflow_client = AirflowClient(
            airflow_url=airflow_url,
            username=airflow_user,
            password=airflow_pass,
            api_token=airflow_token,
            request_timeout=airflow_timeout,
        )
        self.analysis_dag_id = os.getenv('AIRFLOW_ANALYSIS_DAG_ID', 'medgemma_analysis_pipeline')
        self.zip_dag_id = os.getenv('AIRFLOW_ZIP_DAG_ID', 'girder_zip_pipeline')
        self.processed_item_name = os.getenv('ZIP_OUTPUT_ITEM_NAME', 'Processed Dicom')

    def _default_output_item_name(self, source_file_name):
        """Build output item name as <source_file_name_without_ext>_triage."""
        stem = Path(source_file_name or '').stem.strip()
        if not stem:
            return self.processed_item_name
        return f"{stem}_triage"

    def _token_value(self):
        token = self.getCurrentToken()
        if isinstance(token, dict):
            if token.get('token'):
                return token.get('token')
            # Some Girder auth flows do not expose raw token string in token model.
            if token.get('accessToken'):
                return token.get('accessToken')
        if isinstance(token, str):
            return token
        try:
            return (
                cherrypy.request.headers.get('Girder-Token')
                or cherrypy.request.headers.get('girder-token')
            )
        except Exception:
            return None
        return None

    def _latest_zip_file(self, item):
        files = list(Item().childFiles(item))
        zip_files = [f for f in files if f.get('name', '').lower().endswith('.zip')]
        if not zip_files:
            return None
        zip_files.sort(key=lambda f: f.get('created', ''), reverse=True)
        return zip_files[0]

    def _already_processed_item(self, source_item_id, folder_id, processed_item_name):
        """Return processed output item if it already exists for source item."""
        return Item().findOne({
            'folderId': folder_id,
            'name': processed_item_name,
            'meta.source_item_id': source_item_id,
        })

    def _set_trigger_metadata(self, item, dag_id, dag_run):
        current_user = self.getCurrentUser() or {}
        metadata = {
            'airflow_dag_id': dag_id,
            'airflow_job_id': dag_run.get('dag_run_id'),
            'analysis_status': dag_run.get('state', 'queued'),
            'job_started': dag_run.get('logical_date'),
            'triggered_by': current_user.get('login', current_user.get('_id')),
            'triggered_at': datetime.now(timezone.utc).isoformat(),
        }
        Item().setMetadata(item, metadata)
        return metadata

    @access.user
    @autoDescribeRoute(
        Description('Trigger ZIP -> Linux -> Girder Airflow pipeline from an item ZIP')
        .modelParam('id', 'The item ID', model=Item, level=AccessType.WRITE)
        .param('folder_id', 'Optional destination folder id (for creating new item)', required=False)
        .param('item_name', 'Optional new item name if folder_id is used', required=False)
    )
    def trigger_zip_pipeline(self, item, folder_id, item_name):
        """Trigger the ZIP processing DAG from a ZIP file in the selected item."""
        zip_file = self._latest_zip_file(item)
        if not zip_file:
            return {"error": "No ZIP file found in item"}

        girder_url = os.getenv('GIRDER_URL', 'http://localhost:8080')
        girder_token = self._token_value()
        if not girder_token:
            return {"error": "No Girder API token in current request context"}

        item_meta = item.get('meta', {})
        current_status = item_meta.get('analysis_status')
        if current_status in ('queued', 'running'):
            return {
                "status": "in_progress",
                "warning": "Processing is already running for this item.",
                "job_id": item_meta.get('airflow_job_id'),
                "dag_id": item_meta.get('airflow_dag_id', self.zip_dag_id),
            }

        source_item_id = str(item['_id'])
        target_folder_id = folder_id or str(item['folderId'])
        target_item_name = item_name or self._default_output_item_name(zip_file.get('name'))
        existing_processed = self._already_processed_item(
            source_item_id, target_folder_id, target_item_name
        )
        if existing_processed or item_meta.get('processed_dicom_ready'):
            return {
                "status": "already_processed",
                "warning": "Image is already processed for this item.",
                "processed_item_id": str((existing_processed or {}).get('_id', '')),
                "processed_item_name": target_item_name,
            }

        job_id = str(uuid.uuid4())
        dag_run_id = f"manual__girder_{job_id}"
        dag_conf = {
            'job_id': job_id,
            'file_id': str(zip_file['_id']),
            'file_name': zip_file['name'],
            'girder_url': girder_url,
            'girder_token': girder_token,
            'remote_zip_path': os.getenv('ZIP_REMOTE_PATH', '/tmp/girder_zips/'),
            'source_item_id': source_item_id,
            'folder_id': target_folder_id,
            'item_name': target_item_name,
        }

        try:
            dag_run = self.airflow_client.trigger_dag(
                self.zip_dag_id, dag_conf, dag_run_id=dag_run_id
            )
            self._set_trigger_metadata(item, self.zip_dag_id, dag_run)
            return {
                "status": "ZIP pipeline started",
                "dag_id": self.zip_dag_id,
                "job_id": dag_run.get('dag_run_id'),
                "item_id": str(item['_id']),
                "folder_id": target_folder_id,
                "file_id": str(zip_file['_id']),
                "file_name": zip_file['name'],
                "output_item_name": target_item_name,
                "message": "Use /api/v1/medgemma/zip-status/{job_id} for state checks",
            }
        except Exception as e:
            return {"error": f"Failed to trigger ZIP pipeline: {str(e)}"}

    @access.user
    @autoDescribeRoute(
        Description('Analyze DICOM series with MedGemma via Airflow')
        .modelParam('id', 'The item ID', model=Item, level=AccessType.WRITE)
        .param('hf_token', 'Hugging Face token', required=False)
    )
    def analyze_item(self, item, hf_token):
        """Trigger Airflow pipeline for DICOM analysis"""
        # Get item files
        files = list(Item().childFiles(item))

        # Check for ZIP file or DICOM files
        zip_file = None
        dicom_files = []

        for f in files:
            if f['name'].endswith('.zip'):
                zip_file = f
            elif f['name'].endswith('.dcm'):
                dicom_files.append(f)

        if not zip_file and not dicom_files:
            return {"error": "No ZIP or DICOM files found in item"}

        # Generate unique job ID
        job_id = str(uuid.uuid4())

        # Prepare DAG configuration
        girder_url = os.getenv('GIRDER_URL', 'http://localhost:8080')
        hf_token = hf_token or os.getenv("HUGGINGFACE_TOKEN")

        if not hf_token:
            return {"error": "Hugging Face token not provided"}

        # Prepare DAG configuration
        dag_conf = {
            'job_id': job_id,
            'item_id': str(item['_id']),
            'girder_url': girder_url,
            'girder_token': self._token_value(),
            'hf_token': hf_token,
            'extract_dir': f'/tmp/medgemma_extract_{job_id}',
            'anonymized_dir': f'/tmp/medgemma_anonymized_{job_id}',
            'output_dir': f'/tmp/medgemma_output_{job_id}',
        }

        # Add ZIP file info if available
        if zip_file:
            dag_conf['file_id'] = str(zip_file['_id'])
            dag_conf['remote_zip_path'] = f'/tmp/medgemma_work/{zip_file["name"]}'

        # Trigger Airflow DAG
        try:
            dag_run = self.airflow_client.trigger_dag(
                self.analysis_dag_id, dag_conf, dag_run_id=f"manual__analysis_{job_id}"
            )
            self._set_trigger_metadata(item, self.analysis_dag_id, dag_run)
            return {
                "status": "Analysis pipeline started",
                "dag_id": self.analysis_dag_id,
                "job_id": dag_run.get('dag_run_id'),
                "item_id": str(item['_id']),
                "message": "Check status using /api/v1/medgemma/status/{job_id}"
            }
        except Exception as e:
            return {"error": f"Failed to trigger pipeline: {str(e)}"}
    
    @access.user
    @autoDescribeRoute(
        Description('Get status of MedGemma analysis job')
        .param('job_id', 'The Airflow DAG run ID', required=True)
    )
    def get_job_status(self, job_id):
        """Get status of Airflow pipeline job"""
        try:
            dag_run_status = self.airflow_client.get_dag_run_status(
                self.analysis_dag_id,
                job_id
            )

            return {
                "job_id": job_id,
                "dag_id": self.analysis_dag_id,
                "status": dag_run_status.get('state', 'unknown'),
                "start_date": dag_run_status.get('start_date'),
                "end_date": dag_run_status.get('end_date'),
                "dag_run_id": dag_run_status.get('dag_run_id'),
            }
        except Exception as e:
            return {"error": f"Failed to get job status: {str(e)}"}

    @access.user
    @autoDescribeRoute(
        Description('Get status of ZIP pipeline job')
        .param('job_id', 'The Airflow DAG run ID', required=True)
    )
    def get_zip_job_status(self, job_id):
        """Get status of ZIP workflow DAG run."""
        try:
            dag_run_status = self.airflow_client.get_dag_run_status(self.zip_dag_id, job_id)
            state = dag_run_status.get('state', 'unknown')

            progress = {
                "percent": 0,
                "done_tasks": 0,
                "total_tasks": 0,
            }
            try:
                task_data = self.airflow_client.get_dag_run_tasks(self.zip_dag_id, job_id)
                task_instances = task_data.get('task_instances', [])
                total_tasks = len(task_instances)
                done_states = {'success', 'failed', 'skipped', 'upstream_failed'}
                done_tasks = sum(1 for t in task_instances if t.get('state') in done_states)
                percent = int((done_tasks / total_tasks) * 100) if total_tasks else 0
                if state == 'success':
                    percent = 100
                progress = {
                    "percent": percent,
                    "done_tasks": done_tasks,
                    "total_tasks": total_tasks,
                }
            except Exception:
                # Keep status endpoint resilient even if task-instance API fails.
                if state == 'success':
                    progress["percent"] = 100

            source_item = Item().findOne({'meta.airflow_job_id': job_id})
            if source_item:
                update_meta = {'analysis_status': state}
                if state == 'success':
                    update_meta['processed_dicom_ready'] = True
                Item().setMetadata(source_item, update_meta)

            return {
                "job_id": job_id,
                "dag_id": self.zip_dag_id,
                "status": state,
                "start_date": dag_run_status.get('start_date'),
                "end_date": dag_run_status.get('end_date'),
                "dag_run_id": dag_run_status.get('dag_run_id'),
                "progress": progress,
            }
        except Exception as e:
            return {"error": f"Failed to get ZIP job status: {str(e)}"}

    @access.user
    @autoDescribeRoute(
        Description('Get latest pipeline status for an item')
        .modelParam('id', 'The item ID', model=Item, level=AccessType.READ)
    )
    def get_item_pipeline_status(self, item):
        """Return latest item pipeline metadata and refresh status from Airflow if possible."""
        metadata = item.get('meta', {})
        dag_id = metadata.get('airflow_dag_id')
        dag_run_id = metadata.get('airflow_job_id')
        if not dag_id or not dag_run_id:
            return {
                "item_id": str(item['_id']),
                "status": metadata.get('analysis_status', 'not_started'),
                "message": "No Airflow run metadata found on item",
            }

        try:
            dag_run_status = self.airflow_client.get_dag_run_status(dag_id, dag_run_id)
            state = dag_run_status.get('state', 'unknown')
            Item().setMetadata(item, {'analysis_status': state})
            return {
                "item_id": str(item['_id']),
                "job_id": dag_run_id,
                "dag_id": dag_id,
                "status": state,
                "start_date": dag_run_status.get('start_date'),
                "end_date": dag_run_status.get('end_date'),
            }
        except Exception as e:
            return {
                "item_id": str(item['_id']),
                "job_id": dag_run_id,
                "dag_id": dag_id,
                "status": metadata.get('analysis_status', 'unknown'),
                "error": f"Status refresh failed: {str(e)}",
            }


def load(info):
    """Load the plugin"""
    info['apiRoot'].medgemma = MedGemmaResource()


class MedGemmaGirderPlugin(GirderPlugin):
    DISPLAY_NAME = 'MedGemma'
    CLIENT_SOURCE_PATH = '../web_client'

    def load(self, info):
        load(info)
