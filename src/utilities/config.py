from configparser import ConfigParser
from os import path


def get_config():
    if not path.exists("config.ini"):
        init_config()

    config = ConfigParser()
    config.read(filenames="config.ini")
    return config


def init_config():
    # Create a ConfigParser object
    config = ConfigParser()

    # Add a section for database settings
    config.add_section("twitter")

    # Set the default values for the options in the database section
    config.set("twitter", "app_key", "")
    config.set("twitter", "app_secret", "")
    config.set("twitter", "access_token", "")
    config.set("twitter", "access_secret", "")
    config.set("twitter", "bearer_token", "")

    # Add a section for application settings
    config.add_section("twitch")

    # Set the default values for the options in the application section
    config.set("twitch", "client_id", "")
    config.set("twitch", "client_secret", "")
    config.set("twitch", "refresh_token", "")

    config.add_section("discord")

    config.set("discord", "webhooks", "")

    # Save the configuration to a file
    with open("config.ini", "w") as configfile:
        config.write(configfile)
