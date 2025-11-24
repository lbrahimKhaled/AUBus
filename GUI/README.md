# GUI
This folder contains the graphical interface for the project.  
It provides an interactive front-end that connects to the backend server to visualize and control its main features.


## Configuration / Dependencies
```bash
pip install pyQt5
pip install requests
```

## Running the client GUI:
```bash
python -m GUI.frontend
```

-> the terminal will prompt you to insert the IP of the server; how to get it?
when you ran the server code it must have looked like the following:

```bash
ibrahimkhaled@Mac AUBus % python -m backend.connections.server.run
Server is listening on port 9999 and ip: 192.168.1.142
```

you copy the ip from the server and answer the question in your frontend terminal:

```bash
ibrahimkhaled@Mac AUBus % python -m GUI.frontend
enter IP: 192.168.1.142 (<- this is the answer that we got from above)
```