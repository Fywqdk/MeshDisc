# MeshDisc Privacy Policy

*Effective October 24, 2026*

This policy describes what data the MeshDisc Discord bot processes. In short: the bot does not store any personal data about Discord users.

## Data from Discord

- The bot only uses Discord's default intents and does **not** have access to the content of messages written in Discord.
- When you use `/mesh status` or `/mesh pause`, the bot processes the command and replies only to you. Your user ID, name and other details are not stored.
- The bot knows the names and IDs of the servers and channels it has been invited to, so that it can post. These are not kept beyond the running process.

## Data from the MeshCore network

The bot receives radio packets heard by a MeshCore node. For messages in channels it is configured to read, it posts the following to Discord:

- the sender's name, as chosen by the sender on their own node
- the message text and time
- the channel name
- technical details: signal strength (SNR/RSSI), hop count and the repeater IDs along the route

These are messages sent in channels that anyone with the channel name or key can read. Messages in channels the bot has no key for, as well as direct messages, cannot be read and are not posted.

## Retention

- The bot has no database. Statistics and a short-lived duplicate filter (60 seconds by default) are kept in memory only and are lost on restart.
- Operational logs may contain technical error messages, but no data about Discord users.
- Messages posted to Discord are stored by Discord under the [Discord Privacy Policy](https://discord.com/privacy) and can be deleted by the server's moderators.

## Sharing

Data is not sold or shared with third parties. Nothing is sent anywhere other than Discord.

## Your rights

If you want a message removed from the Discord channel, contact the server's moderators. Questions about this policy can be raised by opening an issue at [github.com/Fywqdk/MeshDisc](https://github.com/Fywqdk/MeshDisc/issues).

## Changes

This policy may be updated. The current version is always available in this repository, and changes can be seen in its history.
