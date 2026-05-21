from utils.database import get_database
from core.config import get_config

cfg = get_config()
db = get_database(cfg)
r = db.get_results(limit=5)
for x in r:
    print(f"id={x.get('id')}, image_path={x.get('image_path')}, image_name={x.get('image_name')}")
