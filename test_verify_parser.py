import sys
from tickets_parser import parse_ticket_message

test_messages = [
    """
    World Cup Stock and Prices

    Match 002
    CAT 3 (40) - $325
    CAT 4 (5) - $300

    Match 004
    CAT 3 (42) - $1150

    Match 005
    CAT 2 (4) - $1000

    Match 006
    CAT 3 (54) - $300

    Match 009
    CAT 3 (52) - $450

    Match 011
    CAT 3 (32) - $500
    """,
    # Test Mixed format
    """
    Match 102
    Cat 1 (2) - 1500
    """
]

print("Running Parser Verification...")

for i, msg in enumerate(test_messages):
    print(f"\n--- Test Message {i+1} ---")
    result = parse_ticket_message(msg)
    
    # Check general status
    print(f"Status: {result.get('parse_status')}")
    print(f"Match: {result.get('match')}")
    print(f"Lines Found: {len(result.get('lines', []))}")
    
    # Print lines details
    for line in result.get('lines', []):
        row_match = line.get('match')
        cat = line.get('category')
        qty = line.get('quantity')
        price = line.get('price')
        curr = line.get('currency')
        print(f"  -> Match: {row_match}, Cat: {cat}, Qty: {qty}, Price: {price} {curr}")

print("\nVerification Complete.")
