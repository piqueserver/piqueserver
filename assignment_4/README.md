# Report for assignment 4

## Project

Name: Piqueserver

URL: [https://github.com/piqueserver/piqueserver](https://github.com/piqueserver/piqueserver)

A server implementation for the game Ace of Spades 0.75. Piqueserver further extends PySnip, an older, inactive server project.

## Complexity

## Coverage

### High cyclomatic complexity functions

We used lizard to generate the cyclomatic complexety for each function in the project and then chose the top 10.


1. `piqueserver::scripts::badmin.py::score_grief()` (CCN = 39)  
The `badmin.py` module is a bot that do some common administrative tasks, This particular function tries to set a score a players behaviour on the server in terms of player behaviour. Higher score means the player might be harassing other players. One part of this calculation is done by looking at how the player interacts with teammate blocks. Right now this is done with numerous `if/else` statements but could be implemented as a function instead.

2. `piqueserver::scripts::blockinfo.py::grief_check()` (CCN = 38)  
This is an admin command that prints information about player interaction with blocks. The idea is to give some metrics about behaviour that can be used to infer if the player is griefing. The cyclomatic complexity is high since a lot of `if`-statements are used to format the string returned from the function. It could be considerably lowered if the result was just the numbers instead of a string describing the implication of the numbers. Also, if the return result shouldn't be altered, the complexity could be lowered by refactoring.

3. `piqueserver::server.py::FeatureProtocol::__init__()` (CCN = 29)  
The constructor of one of the main classes of the whole project. The complexity arises from a few different reasons:
    * Configuration files are read from disk and exceptions has to be handled.
    * After reading configuration files it parses options in one of them.
    * The class inherits from `pyspades::server.py::ServerProtocol` and changes a couple of internally used configuration parameters to a new format.
    All of the above are done with either `if/else` or `try/except`. Complexity could be significantly reduced by writing configuration files in, for example JSON.

4. `pyspades/player.py/on_block_action_recieved()` (CCN = 25)  
The validity of player block construction and destruction are checked here. A lot of conditions has to be fulfilled for a block to be placed or destroyed. These checks are done in nested `if/else` statements. Due to the nature of this code, cyclomatic complexity are expected to be high but the current implementation could probably be refactored to lower it a bit.

5. `pyspades/client.py/loader_receied()` (CCN = 20)  
Loaders handles various network related stuff, like streaming a map from the server to the client or player position updates. Basically the function takes a domain specific packet as input and handles it. There seems to be a lot of unused code (`if` statements followed by `pass`) which could be removed to lower complexity, but in general, the way the project works now, it needs to be high. If the packages were adhered to a strict interface, perhaps functionality could be moved there which would reduce complexity significantly, but this would be a quite big refactorization.

6. `pyspades/player.py/on_position_update_recieved()` (CCN = 20)  
Called when a player changes position. A lot of checks has to be made both in regards of the validity of the new position and the consequences. For example, if the game are a capture the flag game, and the new position is close enough to capture the enemy flag, trigger that functionality. High complexity is, perhaps not necessary, but at least motivated from the functionality. Refactoring could lower it by moving all  checks as whether the new position is valid to a separate function and using separate functions depending on game mode.

7. `pyspades/player.py/grenade_exploded()` (CCN = 20)  
Handles grenade explosion. The function checks if the location if the grenade is valid, if the players hit by it will be affected and in what way the world will be affected. Complexity could be lowered by, for example, implementing a `player.py::hit_by_grenade`-method or similar.

8. `pyspades/player.py/on_input_data_recieved()` (CCN = 19)  
Handles the player input in terms of movement. Again, some checks in terms of the validity of the action is done. Like the above, complexity could probably be lowered but is not needlessly high.

9. `piqueserver/run.py/main()` (CCN = 16)  
The entry point to the server program which parses a lot of command line arguments. There are some redundant `if`-statement but generally, complexity is inherently high. Command line argument parsing (and handling) could be delegated to a library or handled by, for example, a dict of functions, which might lower the cyclomatic complexity.

10. `piqueserver/server.py/run()` (CCN = 14)  
Starts the server. Like the `FeatureProtocol` constructor, most of the cyclomatic complexity here arises from file IO (and the `try/except` associated with them) and probably should be left as it is. The actual complexity is not overwhelming.

### Tools

### DYI

### Evaluation

## Effort spent

|                     |Jonas|David|Safir|Robert|Fredrik|
|---------------------|-----|-----|-----|------|-------|
|Planning             |     |     |     |      |       |
|Discussions          |     |     |     |      |       |
|Reading documentation|     |     |     |      |       |
|Configuration        |     |     |     |      |       |
|Analyzing code/output|     |     |     |      |       |
|Writing documentation|     |     |     |      |       |
|Writing code         |     |     |     |      |       |
|Running code         |     |     |     |      |       |

## Overall experience
