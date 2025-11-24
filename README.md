# AUBus
AUBus is a Python-based carpooling platform for AUB students that connects drivers and passengers through a hybrid client-server/P2P architecture with multithreading. It supports account creation, ride scheduling, area-based driver search, ride requests, chat, and ratings via a custom TCP/UDP protocol.

# TO-DOs in this PR: (we can do them in seperate PR s)
- add the peer to peer functionality (both frontend and backend)
- add the driver request
- if I connected to the driver do I lose the connection to the server (i.e. multithreading or not for the client too?)
-handle weather requests (probably multithreading)