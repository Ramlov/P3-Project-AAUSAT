command = {"az": "200", "el": "131"}
#command = {"direction": "MU"}
operation =[]

for key, value in command.items():
    if key == "el":
        operation.append(key+value)
    elif key == "az":
        operation.append(key+value)
    else:
        operation.append(value)

for item in operation:
    print(item)