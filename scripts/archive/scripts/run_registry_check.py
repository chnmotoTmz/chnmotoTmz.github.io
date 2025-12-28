import importlib
importlib.invalidate_caches()
import src.services.framework.service_registry as sr
print('service_registry imported; registered modules count =', len(sr.service_registry._modules))
print('Sample modules:', list(sr.service_registry._modules.keys())[:20])
