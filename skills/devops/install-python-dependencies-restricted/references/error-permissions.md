# Permission Errors in Umbrel Container

When installing Python packages in Hermes Agent on UmbrelOS, writes to
/usr/lib/pythonX.X/site-packages require elevated privileges. Solution:

1. Use apt-get install via host:
   sudo apt-get install -y python3-feedparser python3-pip

2. Or modify Dockerfile to include:
   RUN apt-get update && \
       apt-get install -y python3-feedparser python3-pip

3. Ownership fix:
   Ensure files stay in /opt/data for persistent access, but note:
   /mnt/c/... paths expire after container restart