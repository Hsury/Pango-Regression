#!/usr/bin/env python3.7

import json
import psutil

print(json.dumps({
    'cpu_usage': psutil.cpu_percent(),
    'memory_free': round(psutil.virtual_memory().available / 1024 / 1024 / 1024, 2),
}))
