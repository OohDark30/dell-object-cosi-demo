import uuid

from minimal import create_app
import os

os.environ["SESSION_SECRET"]="MySessionSecret"
os.environ["FLASE_DEBUG"]="1"
app = create_app()
app.run()

