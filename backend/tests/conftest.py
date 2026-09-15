# backend/tests 专用 conftest：将 backend/ 加入 sys.path，使 app 包可导入
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
