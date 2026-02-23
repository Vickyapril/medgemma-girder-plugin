"""
Airflow Integration Module
Handles communication between Girder and Airflow
"""
import requests
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class AirflowClient:
    """Client for interacting with Airflow REST API"""

    def __init__(
        self,
        airflow_url: str = "http://localhost:8080",
        username: str = "admin",
        password: str = "admin",
        api_token: Optional[str] = None,
        request_timeout: int = 30,
    ):
        """
        Args:
            airflow_url: Airflow webserver URL
            username: Airflow username (used when api_token is not set)
            password: Airflow password (used when api_token is not set)
            api_token: Airflow API bearer token for service account auth
            request_timeout: HTTP timeout in seconds for Airflow API calls
        """
        self.airflow_url = airflow_url.rstrip('/')
        self.username = username
        self.password = password
        self.request_timeout = request_timeout
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        if api_token:
            self.session.headers.update({"Authorization": f"Bearer {api_token}"})
        else:
            self.session.auth = (username, password)
        self.api_base = f"{self.airflow_url}/api/v2"
    
    def trigger_dag(self, dag_id: str, conf: Dict = None, dag_run_id: Optional[str] = None) -> Dict:
        """
        Trigger a DAG run
        
        Args:
            dag_id: DAG identifier
            conf: Configuration dictionary to pass to DAG
        
        Returns:
            DAG run information
        """
        url = f"{self.api_base}/dags/{dag_id}/dagRuns"

        payload = {
            "conf": conf or {},
            # Airflow 3 API requires logical_date for DAG run creation.
            "logical_date": datetime.now(timezone.utc).isoformat(),
        }
        if dag_run_id:
            payload["dag_run_id"] = dag_run_id

        try:
            response = self.session.post(url, json=payload, timeout=self.request_timeout)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Triggered DAG {dag_id}, run_id: {result.get('dag_run_id')}")
            return result
        except requests.exceptions.RequestException as e:
            response_text = getattr(getattr(e, "response", None), "text", "")
            logger.error(f"Failed to trigger DAG: {e} | response={response_text}")
            raise RuntimeError(f"Failed to trigger DAG {dag_id}: {e}") from e
    
    def get_dag_run_status(self, dag_id: str, dag_run_id: str) -> Dict:
        """
        Get status of a DAG run
        
        Args:
            dag_id: DAG identifier
            dag_run_id: DAG run identifier
        
        Returns:
            DAG run status information
        """
        url = f"{self.api_base}/dags/{dag_id}/dagRuns/{dag_run_id}"

        try:
            response = self.session.get(url, timeout=self.request_timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            response_text = getattr(getattr(e, "response", None), "text", "")
            logger.error(f"Failed to get DAG run status: {e} | response={response_text}")
            raise RuntimeError(f"Failed to get DAG run status for {dag_run_id}: {e}") from e
    
    def get_task_status(self, dag_id: str, dag_run_id: str, task_id: str) -> Dict:
        """
        Get status of a specific task
        
        Args:
            dag_id: DAG identifier
            dag_run_id: DAG run identifier
            task_id: Task identifier
        
        Returns:
            Task status information
        """
        url = f"{self.api_base}/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances/{task_id}"

        try:
            response = self.session.get(url, timeout=self.request_timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            response_text = getattr(getattr(e, "response", None), "text", "")
            logger.error(f"Failed to get task status: {e} | response={response_text}")
            raise RuntimeError(f"Failed to get task status for {task_id}: {e}") from e

    def get_dag_run_tasks(self, dag_id: str, dag_run_id: str) -> Dict:
        """Get all task instances for a DAG run."""
        url = f"{self.api_base}/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances"
        try:
            response = self.session.get(url, timeout=self.request_timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            response_text = getattr(getattr(e, "response", None), "text", "")
            logger.error(f"Failed to get task instances: {e} | response={response_text}")
            raise RuntimeError(f"Failed to get task instances for {dag_run_id}: {e}") from e
