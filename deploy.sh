sudo apt-get install sshpass
sshpass -p SSH_PASSWORD ssh SSH_URL cd /opt/discord-bot && docker-compose down && docker rmi $(docker images -a -q) && docker-compose up -d