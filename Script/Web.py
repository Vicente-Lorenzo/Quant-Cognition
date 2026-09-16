import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Library.Web.App import WebAppAPI

if __name__ == "__main__":
    WebAppAPI.build(debug=True).run()