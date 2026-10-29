import csv
import io
import genanki
import random
from schemas import GeneratedCard

def export_to_csv(cards: list[GeneratedCard]) -> str:
    """
    Converts a list of cards into a CSV-formatted string.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write the header row
    writer.writerow(["Question", "Answer"])
    
    # Write each card
    for card in cards:
        writer.writerow([card.question, card.answer])
        
    return output.getvalue()

def export_to_anki(cards: list[GeneratedCard], deck_name: str = "Local AI Study Deck") -> bytes:
    """
    Converts a list of cards into an Anki .apkg file (as raw bytes).
    """
    # genanki requires a unique ID for the model and deck.
    my_model = genanki.Model(
        1607392319, # Random model ID
        'Simple Model',
        fields=[
            {'name': 'Question'},
            {'name': 'Answer'},
        ],
        templates=[
            {
                'name': 'Card 1',
                'qfmt': '{{Question}}',
                'afmt': '{{FrontSide}}<hr id="answer">{{Answer}}', # Back of card
            },
        ])

    # 2. Create the Deck
    my_deck = genanki.Deck(
        2059400110,
        deck_name
    )

    for card in cards:
        note = genanki.Note(
            model=my_model,
            fields=[card.question, card.answer]
        )
        my_deck.add_note(note)

    # genanki creates a temporary file on your hard drive, so we use a workaround 
    # to write it to memory instead using genanki's Package class.
    package = genanki.Package(my_deck)
    
    # (FastAPI needs bytes to serve a file download)
    apkg_bytes = package.write_to_file("temp_deck.apkg") 
    
    # Read the bytes and delete the temp file
    with open("temp_deck.apkg", "rb") as f:
        file_bytes = f.read()
        
    import os
    os.remove("temp_deck.apkg")
    
    return file_bytes