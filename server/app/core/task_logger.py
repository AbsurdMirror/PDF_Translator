import os
import yaml
import logging
import datetime
from pathlib import Path
from .config import TASKS_DIR

logger = logging.getLogger(__name__)

class TaskLogger:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.task_dir = TASKS_DIR / task_id
        self.log_file = self.task_dir / "network.log.yaml"

        # Ensure directory exists
        if not self.task_dir.exists():
            try:
                self.task_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create task dir for logging: {e}")

    def log(self, action: str, request: dict = None, response: dict = None, error: str = None, service: str = None):
        """
        Logs a network action to the task's network log file.
        """
        entry = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
            "action": action,
            "service": service,
        }

        if request:
            entry["request"] = request
        if response:
            entry["response"] = response
        if error:
            entry["error"] = str(error)

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write("---\n")
                yaml.safe_dump(entry, f, allow_unicode=True, sort_keys=False)
                f.write("\n")
        except Exception as e:
            logger.error(f"Failed to write to task log: {e}")

# Helper function for easy usage
def log_task_network(task_id: str, action: str, **kwargs):
    if not task_id:
        return
    TaskLogger(task_id).log(action, **kwargs)
