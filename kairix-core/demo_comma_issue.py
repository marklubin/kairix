# Demonstrating how trailing comma breaks property definitions

class Example1:
    # WITHOUT trailing comma - this is a property
    vector_address = "I am a property"
    
class Example2:
    # WITH trailing comma - this becomes a tuple!
    vector_address = "I am a property",

# Let's see the difference:
print("Example1.vector_address:", Example1.vector_address)
print("Type:", type(Example1.vector_address))

print("\nExample2.vector_address:", Example2.vector_address)
print("Type:", type(Example2.vector_address))

# When you try to set it on an instance:
obj1 = Example1()
obj1.vector_address = "New value"
print("\nobj1.vector_address after setting:", obj1.vector_address)

obj2 = Example2()
# This creates a NEW instance attribute, doesn't use the class property
obj2.vector_address = "New value"
print("obj2.vector_address after setting:", obj2.vector_address)
print("But Example2.vector_address is still:", Example2.vector_address)