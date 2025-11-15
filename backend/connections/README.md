# Server and Client Codes

# Running / Testing some functions : 
to be able to run things as a package and not get "no module named ..." run this command and not from the run button (it will run it as a module) 
DO NOT NAVIGATE TO THE SPECIFIC FILE AND RUN IT
```bash
cd yourpathtoAUBus
python -m subPathToTheSpecificFile
```
and when importing stuff use this:
- "." to go up 1 level (e.g. I am in util.py I write from .(now I am in the server directory)serverCode import func)
- when importing to go to the main directory write ->  ... for as many folders seperating your folder from the AUBus directory

- Alternatively you can go down from the main directory to the specific file we want to import
e.g. to import from backend/connections/server/util.py
```python
from backend.connections.server.util import func
```

# Application Layer Protocol


-for drivers we will have a  

# Configuration
to install dependicies :
```bash
cd backend/connections
pip install -r requirements.txt
