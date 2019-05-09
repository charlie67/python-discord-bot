if [ "$TRAVIS_BRANCH" = "master" -a "$TRAVIS_PULL_REQUEST" = "false" ];
then
    sudo apt-get update
    sudo apt-get install sshpass
    sshpass -p $SSH_PASSWORD ssh $SSH_URL
    cd /opt/discord-bot
    docker-compose down && docker rmi $(docker images -a -q) && docker-compose up -d
    exit
fi