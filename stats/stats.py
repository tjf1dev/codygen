# man i love coding with my boy, he really is the best
# - cody

# json and os lol
import json, os

def add(user, value=1):
    file_path = os.path.join(os.path.dirname(__file__), "stats.json")
    with open(file_path, "r") as file:
        json_object = json.load(file)
    try:
        json_object[user] = json_object[user] + value
    except KeyError: # bro guessed once
        json_object[user] = 1

    with open(file_path, 'w') as outfile:
        json.dump(json_object, outfile)

def getUserValue(user):
    file_path = os.path.join(os.path.dirname(__file__), "stats.json")
    with open(file_path, "r") as file:
        json_object = json.load(file)
    try:
        userValue = json_object[user]
    except KeyError: # bro did not guess anything
        userValue = 0

    return userValue

def getAllValues():
    file_path = os.path.join(os.path.dirname(__file__), "stats.json")
    with open(file_path, "r") as file:
        json_object = json.load(file)

    return json_object