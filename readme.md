# EPFL Discord Bot

Actually does not do much, except run an interpreter for the owner.
To see an interesting bot, got to [tfjm-discord-bot](https://gitlab.com/ddorn/tfjm-discord-bot)

### Install and run

One needs poetry to install the dependencies easily.

```sh
poetry install
poetry shell
```

Once in the shell, you can use `python bot.py` to start it.


##### Nix and direnv

If you use nix, there is a `shell.nix` that provides the right environment. Also, `direnv` is a friend.
