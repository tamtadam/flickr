from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, List


class ThreadPooler:
    """Manages parallel task execution with result collection."""

    def __init__(self, task: Callable, max_workers: int = 0, params: List[dict] | None = None) -> None:
        if params is None:
            params = []
        self.max_workers = max_workers or len(params)
        self.task = task
        self.params = params
        self.results: List[Any] = []

    def add_result(self, result: Any) -> None:
        self.results.append(result)


def execute_in_parallel(tasks: List[ThreadPooler]) -> List[ThreadPooler]:
    for task in tasks:
        with ThreadPoolExecutor(max_workers=task.max_workers) as executor:
            futures = [executor.submit(task.task, **param) for param in task.params]
            for future in as_completed(futures):
                result = future.result()
                task.add_result(result)
    return tasks
