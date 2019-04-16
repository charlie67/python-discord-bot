docker build . --tag charlie67/discord-bot:$TRAVIS_BRANCH-latest
echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
docker push charlie67/discord-bot:$TRAVIS_BRANCH-latest