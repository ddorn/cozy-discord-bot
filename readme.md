# Cozy's Discord Bot

### Features

- Dynamically assign roles and individual channel permissions 
    based on other roles
- Full interactive interpreter for the owner
- Full bot reloading, including the bot class itself
- Complex and automatic persistent storage for Cogs settings and data
- Per-guild cogs settings modifiable with commands
- Hugs between members with statistcs
- Simple calculations
- Fractal generation
- Custom automatic help system
- Setup reminders
- Jokes system were people can add jokes, up/downvote them 
    and send random jokes
- Simple moderation tools:
    - Delete a range of messages
    - freeze a channel for a given time
    - hide a channel for a given time
    - send private messages via the bot
    - send embed with every parameter customisable

### Install and run

One needs poetry to install the dependencies easily.

```shell script
poetry install
DISCORD_TOKEN=xxxxxx poetry run python .
```

##### Nix and direnv

If you use nix, there is a `shell.nix` that provides the right environment. Also, `direnv` is a friend.
