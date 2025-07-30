import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from folder.affinity import get_company_by_name

print(get_company_by_name("gridstatus", "gridstatus.io"))
