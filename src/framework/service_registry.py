import os
import importlib
import importlib.util
import sys
import logging

from typing import Dict, Type
from .base_task import BaseTaskModule

logger = logging.getLogger(__name__)

class ServiceRegistry:
    """Discovers and manages available task modules."""

    def __init__(self):
        self._modules: Dict[str, Type[BaseTaskModule]] = {}

    def register_module(self, name: str, module_class: Type[BaseTaskModule]):
        """
        Manually register a task module.

        Args:
            name (str): The name to register the module under
            module_class (Type[BaseTaskModule]): The task module class
        """
        if not issubclass(module_class, BaseTaskModule):
            raise ValueError(f"Module class must be a subclass of BaseTaskModule")
        self._modules[name] = module_class

    def discover_modules(self, module_paths: list[str]):
        """
        Dynamically imports and discovers task modules from specified paths.

        Args:
            module_paths (list[str]): A list of directory paths to search for modules.
        """
        # プロジェクトルート（srcの親ディレクトリ）を固定基準点にする
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        for path in module_paths:
            if not os.path.exists(path):
                logger.warning(f"Module path does not exist, skipping: {path}")
                continue

            abs_path = os.path.abspath(path)
            for root, _, files in os.walk(abs_path):
                for file in files:
                    if file.endswith(".py") and not file.startswith("_"):
                        full_path = os.path.join(root, file)
                        
                        # project_root基準でドット区切りのモジュール名を作成
                        # 例: src/tasks/my_task.py -> src.tasks.my_task
                        rel_path = os.path.relpath(full_path, project_root)
                        module_path = os.path.splitext(rel_path)[0].replace(os.sep, '.')

                        logger.debug(f"Attempting to load module file: {full_path} as {module_path}")
                        try:
                            spec = importlib.util.spec_from_file_location(module_path, full_path)
                            if spec and spec.loader:
                                module = importlib.util.module_from_spec(spec)
                                # 内部インポートが正しく解決されるようpackageを設定
                                module.__package__ = module_path.rpartition('.')[0]
                                sys.modules[module_path] = module
                                spec.loader.exec_module(module)
                            else:
                                raise ImportError(f"Could not create spec for {full_path}")
                            
                            for attribute_name in dir(module):
                                attribute = getattr(module, attribute_name)
                                if not isinstance(attribute, type):
                                    continue

                                if attribute is BaseTaskModule:
                                    continue

                                is_task_subclass = (
                                    issubclass(attribute, BaseTaskModule)
                                    and attribute is not BaseTaskModule
                                )
                                if is_task_subclass:
                                    module_info = attribute.get_module_info()
                                    self._modules[module_info['name']] = attribute
                                    logger.info(f"Registered task module: {module_info['name']} (from {module_path})")

                                # 警告: Taskという名前なのにBaseTaskModuleを継承していないもの
                                if 'Task' in attribute_name and not is_task_subclass:
                                    logger.warning(
                                        f"FrameworkWarning: Class '{attribute_name}' in '{module_path}' "
                                        f"looks like a task but does NOT inherit from BaseTaskModule."
                                    )

                        except Exception as e:
                            logger.error(f"Failed to process module {module_path}: {e}", exc_info=True)

        logger.info(f"Total registered modules: {len(self._modules)}")

    def get_module(self, name: str) -> Type[BaseTaskModule]:
        """
        Retrieves a task module class by its name.

        Args:
            name (str): The name of the module to retrieve.

        Returns:
            Type[BaseTaskModule]: The class of the requested module.

        Raises:
            ValueError: If the module is not found in the registry.
        """
        module_class = self._modules.get(name)
        if not module_class:
            raise ValueError(f"Module '{name}' not found in the registry.")
        return module_class

# Global instance
service_registry = ServiceRegistry()

# discovery対象ディレクトリの設定
current_dir = os.path.dirname(os.path.abspath(__file__)) # src/framework
src_dir = os.path.dirname(current_dir) # src
project_root = os.path.dirname(src_dir) # project root

service_registry.discover_modules([
    os.path.join(src_dir, 'tasks')
])
