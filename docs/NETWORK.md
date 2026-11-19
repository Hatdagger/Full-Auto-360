# Online and LAN play

## What the game does

Full Auto's multiplayer is **Xbox Live only**: up to 8 players, ranked (arbitrated) and player matches, lobbies that survive between races, voice chat. There is no System Link mode: the executable has no System Link text at all, only Live lobby and session code (`HostSession`, `XSessionCreate`, `Ranked Game: Host started arbitrating`, `RETURNING to existing lobby of current session`, ...). Locally it does split screen.

It reaches Xbox Live through the November 2005 XDK libraries (`XONLINE`, `XHV` for voice) and these system calls:

| Group | Imports |
|---|---|
| Sessions / matchmaking | `XamSessionCreateHandle`, `XamSessionRefObjByHandle`, and the `XMsgStartIORequest(Ex)` / `XMsgInProcessCall` messages that carry `XSessionCreate`, search, join, start, end, arbitration and stats |
| Secure networking | `NetDll_XNetStartup`, `XNetGetTitleXnAddr`, `XNetXnAddrToInAddr`, `XNetConnect` |
| Quality of service | `NetDll_XNetQosListen`, `XNetQosLookup`, `XNetQosRelease` |
| Sockets | `socket`, `bind`, `connect`, `listen`, `accept`, `select`, `send`, `recv`, `sendto`, `recvfrom`, `ioctlsocket`, `closesocket`, `WSAStartup`, `WSACleanup`, `WSAGetLastError` |
| Profiles | `XamUserGetSigninState`, `XamUserGetXUID`, `XamUserGetName`, `XamUserCheckPrivilege`, `XamUserAreUsersFriends`, `XamShowSigninUI`, `XamShowFriendsUI`, `XamShowGamerCardUIForXUID` |
| Stats | `XamUserCreateStatsEnumerator`, `XamUserReadProfileSettings`, `XamUserWriteProfileSettings` |
| Voice | `XamVoiceCreate`, `XamVoiceSubmitPacket`, `XamVoiceHeadsetPresent`, `XamVoiceClose` |

## The plan: stand in for Xbox Live

The game keeps thinking it is on Xbox Live. The recomp's runtime answers those calls itself:

1. **Sign-in.** A local profile reports as signed in to Live with multiplayer allowed.
2. **Addresses.** An `XNADDR` carries the player's real IP and port. `XNetXnAddrToInAddr` hands back the real address; the "secure" connection is plain UDP.
3. **Sockets.** Game sockets become host sockets. Xbox VDP sockets (UDP with a small header) map to UDP.
4. **Quality of service.** Probes answer at once with the measured ping, so matchmaking never stalls.
5. **Sessions.** `XSessionCreate` / search / join go to a small lobby service inside the recomp:
   - **LAN:** a session is announced with a UDP broadcast; other PCs on the network list it. No server.
   - **Online:** join by a short code or an IP address. NAT traversal with UPnP and/or hole punching; a relay only as a last resort.
6. **Arbitration (ranked).** The host's result is accepted; stats and leaderboards are kept locally.
7. **Voice.** Off at first.

## Where the code comes from

ReXGlue's XAM is derived from Xenia. [Xenia Canary Netplay](https://github.com/AdrianCassar/xenia-canary) already implements most of the steps above for emulated games and lists **Full Auto** among the titles it supports in some form. Its session, XNet and QoS code is the starting point; it gets moved into this project's runtime layer, with its web-service lookups replaced by the LAN broadcast and join-code paths.

## Order of work

1. Offline first: the game must boot and race (roadmap phases 2 and 3). Until then, network calls report "no network" so the game skips Live.
2. Live menus open with the local profile.
3. Two PCs on one LAN: host a lobby, see it, join, race.
4. Eight players on LAN.
5. Internet play.

## Open decisions

- How players connect online: join codes, IP entry, a public lobby list, or several of these.
- Whether to stay compatible with Xenia Canary Netplay's public server, so recomp players could meet emulator players.
