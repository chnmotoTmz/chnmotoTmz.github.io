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
        if not issubclass(module_class, BaseTaskModule):
            raise ValueError(f"Module class must be a subclass of BaseTaskModule")
        self._modules[name] = module_class

    def discover_modules(self, module_paths: list[str]):
        # project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        for path in module_paths:
            if not os.path.exists(path):
                logger.warning(f"Path not found: {path}")
                continue
                
            for root, _, files in os.walk(path):
                for file in files:
                    if file.endswith(".py") and not file.startswith("_"):
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, project_root)
                        module_path = os.path.splitext(rel_path)[0].replace(os.sep, '.')

                        try:
                            spec = importlib.util.spec_from_file_location(module_path, full_path)
                            if spec and spec.loader:
                                module = importlib.util.module_from_spec(spec)
                                module.__package__ = module_path.rpartition('.')[0]
                                sys.modules[module_path] = module
                                spec.loader.exec_module(module)
                            
                            for attribute_name in dir(module):
                                attribute = getattr(module, attribute_name)
                                if not isinstance(attribute, type): continue
                                if attribute is BaseTaskModule: continue

                                if issubclass(attribute, BaseTaskModule):
                                    info = attribute.get_module_info()
                                    self._modules[info['name']] = attribute
                                    logger.debug(f"Registered: {info['name']}")

                        except Exception as e:
                            logger.error(f"Failed to process {module_path}: {e}")
        
        logger.info(f"Total registered modules: {len(self._modules)}")

    def get_module(self, name: str) -> Type[BaseTaskModule]:
        module_class = self._modules.get(name)
        if not module_class:
            raise ValueError(f"Module '{name}' not found.")
        return module_class

service_registry = ServiceRegistry()
current_dir = os.path.dirname(os.path.abspath(__file__))
# current_dir: src/services/framework
# project_root should be the parent of src
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
service_registry.discover_modules([
    os.path.join(project_root, 'src', 'tasks')
])
