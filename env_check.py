from dotenv import dotenv_values

values = dotenv_values(".env")
print("Keys found:", len(values))
for key, value in values.items():
    if value:
        print(repr(key), "length", len(value))
    else:
        print(repr(key), "EMPTY")