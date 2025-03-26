from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse
import re
from collections import defaultdict
from datetime import datetime
import os
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def index(request):
    return render(request, 'mos3c/index.html')

def try_parse_timestamp(date_str, time_str, am_pm):
    """
    Try parsing the timestamp with multiple possible formats.
    Returns the parsed datetime object or None if all formats fail.
    """
    # List of possible date formats to try
    date_formats = [
        ('%m/%d/%Y', 'MM/DD/YYYY'),  # e.g., 02/25/2023
        ('%d/%m/%Y', 'DD/MM/YYYY'),  # e.g., 25/02/2023
        ('%m/%d/%y', 'MM/DD/YY'),    # e.g., 02/25/23
        ('%d/%m/%y', 'DD/MM/YY'),    # e.g., 25/02/23
    ]

    # Combine date and time for parsing
    timestamp_str = f"{date_str} {time_str} {am_pm}" if am_pm else f"{date_str} {time_str}"

    for date_format, format_name in date_formats:
        try:
            # If AM/PM is present, include it in the format
            if am_pm:
                full_format = f"{date_format} %I:%M %p"
            else:
                full_format = f"{date_format} %H:%M"  # 24-hour format
            timestamp = datetime.strptime(timestamp_str, full_format)
            logger.debug(f"Successfully parsed timestamp '{timestamp_str}' with format '{format_name}'")
            return timestamp
        except ValueError:
            continue

    logger.error(f"Failed to parse timestamp: '{timestamp_str}' with all known formats")
    return None

def upload(request):
    if request.method == 'POST' and request.FILES.get('chat_file'):
        uploaded_file = request.FILES['chat_file']

        # File type validation: Ensure the file is a .txt file
        if not uploaded_file.name.endswith('.txt'):
            return render(request, 'mos3c/upload.html', {
                'error': 'Please upload a .txt file.'
            })

        # Save the file
        fs = FileSystemStorage()
        filename = fs.save(uploaded_file.name, uploaded_file)
        file_path = fs.path(filename)

        # Process the file
        participants = defaultdict(lambda: {'messages': [], 'message_count': 0, 'word_count': 0})
        total_messages = 0
        first_date = None
        last_date = None

        # Read the file with encoding fallback
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='utf-16') as file:
                    lines = file.readlines()
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='latin-1') as file:
                    lines = file.readlines()
        except Exception as e:
            os.remove(file_path)
            return render(request, 'mos3c/upload.html', {
                'error': 'An error occurred while reading the file.'
            })

        # Check if the file is empty
        if not lines:
            os.remove(file_path)
            return render(request, 'mos3c/upload.html', {
                'error': 'The uploaded file is empty.'
            })

        logger.debug(f"Total lines in file: {len(lines)}")
        logger.debug("First 10 lines of the file (for debugging):")
        for i, line in enumerate(lines[:10], 1):
            logger.debug(f"Line {i}: {line.strip()}")

        # Set chat name from file name
        file_name_without_ext = os.path.splitext(uploaded_file.name)[0]
        if "with " in file_name_without_ext:
            chat_name = file_name_without_ext.split("with ", 1)[1]
        else:
            chat_name = file_name_without_ext
        logger.debug(f"Chat name set from file name: {chat_name}")

        # Updated regex to match various timestamp formats
        # Captures: date (e.g., 02/25/2023 or 25/02/2023), time (e.g., 11:18), optional AM/PM, name, message
        message_pattern = re.compile(r'(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2})\s*(AM|PM)?\s*-\s*(.*?):\s*(.*)')

        # Process the lines, handling multi-line messages and skipping system messages
        current_message = []
        current_line = None
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if the line starts with a timestamp (new message)
            match = message_pattern.match(line)
            if match:
                date_str, time_str, am_pm, name, message = match.groups()

                # Skip media or deleted messages
                if "<Media omitted>" in message or "This message was deleted" in message:
                    logger.debug(f"Skipping media or deleted message: {line}")
                    current_message = []
                    current_line = None
                    continue

                # Skip system messages
                system_message_indicators = [
                    "created group",
                    "were added",
                    "changed this group's icon",
                    "messages and calls are end-to-end encrypted",
                    "joined using this group's invite link",
                    "changed the subject to",
                    "changed the group description",
                    "changed their phone number",
                    "added",
                    "removed",
                    "left"
                ]
                if not name or any(indicator in message.lower() for indicator in system_message_indicators):
                    logger.debug(f"Skipping system message: {line}")
                    current_message = []
                    current_line = None
                    continue

                # If we have a previous message being built, process it
                if current_message and current_line:
                    full_message = " ".join(current_message)
                    total_messages += 1
                    logger.debug(f"Counting message #{total_messages}: {full_message}")

                    prev_date_str, prev_time_str, prev_am_pm, prev_name, _ = current_line.groups()
                    # Convert date from short year (YY) to full year (YYYY)
                    parts = prev_date_str.split('/')
                    if len(parts[2]) == 2:  # YY format
                        parts[2] = f"20{parts[2]}"  # Assume 20XX
                    prev_date_str = '/'.join(parts)

                    # Try parsing the timestamp with multiple formats
                    timestamp = try_parse_timestamp(prev_date_str, prev_time_str, prev_am_pm)
                    if timestamp is None:
                        logger.debug(f"Skipping message due to unparseable timestamp: {full_message}")
                        current_message = []
                        current_line = None
                        continue

                    if first_date is None or timestamp < first_date:
                        first_date = timestamp
                    if last_date is None or timestamp > last_date:
                        last_date = timestamp

                    # Update participant data
                    participants[prev_name]['messages'].append(full_message)
                    participants[prev_name]['message_count'] += 1
                    words = clean_and_tokenize(full_message)
                    participants[prev_name]['word_count'] += len(words)

                # Start a new message
                current_message = [message]
                current_line = match
            else:
                # If the line doesn't start with a timestamp, it's part of a multi-line message
                if current_message:
                    current_message.append(line)
                    logger.debug(f"Appending to multi-line message: {line}")
                else:
                    logger.debug(f"Skipping line (not part of a message): {line}")
                    continue

        # Process the last message if it exists
        if current_message and current_line:
            full_message = " ".join(current_message)
            total_messages += 1
            logger.debug(f"Counting message #{total_messages}: {full_message}")

            date_str, time_str, am_pm, name, _ = current_line.groups()
            # Convert date from short year (YY) to full year (YYYY)
            parts = date_str.split('/')
            if len(parts[2]) == 2:  # YY format
                parts[2] = f"20{parts[2]}"  # Assume 20XX
            date_str = '/'.join(parts)

            # Try parsing the timestamp with multiple formats
            timestamp = try_parse_timestamp(date_str, time_str, am_pm)
            if timestamp is not None:
                if first_date is None or timestamp < first_date:
                    first_date = timestamp
                if last_date is None or timestamp > last_date:
                    last_date = timestamp

                # Update participant data
                participants[name]['messages'].append(full_message)
                participants[name]['message_count'] += 1
                words = clean_and_tokenize(full_message)
                participants[name]['word_count'] += len(words)

        logger.debug(f"Total messages processed: {total_messages}")
        logger.debug(f"Participants: {dict(participants)}")
        logger.debug(f"First date: {first_date}")
        logger.debug(f"Last date: {last_date}")
        logger.debug(f"Chat name: {chat_name}")

        # Check if any valid messages were found
        if total_messages == 0:
            os.remove(file_path)
            return render(request, 'mos3c/upload.html', {
                'error': 'No valid messages found in the file. Please ensure it is a valid WhatsApp chat export.'
            })

        # Calculate time span in days
        if first_date and last_date:
            time_span_days = (last_date - first_date).days + 1
            if time_span_days < 1:
                time_span_days = 1
        else:
            time_span_days = 1
        logger.debug(f"Time span: {time_span_days} days")

        # Calculate overall stats for statistics cards
        stats = {
            'total_messages': total_messages,
            'users_messages': total_messages,  # Consider renaming or removing this redundant field
            'avg_messages_per_day': round(total_messages / time_span_days, 1),
        }

        # Calculate participant metrics for the table
        participant_data = []
        # Expanded stop words list
        stop_words = {
            'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours', 'yourself',
            'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her', 'hers', 'herself', 'it', 'its', 'itself',
            'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that',
            'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as',
            'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through',
            'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off',
            'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how',
            'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
            'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', 'should',
            'now', 'u', 'im', 'ur'
        }
        for name, data in participants.items():
            message_count = data['message_count']
            word_count = data['word_count']
            avg_messages_per_day = round(message_count / time_span_days, 2)
            avg_words_per_day = round(word_count / time_span_days, 1)

            # Find the most used word, excluding stop words
            word_freq = defaultdict(int)
            for message in data['messages']:
                words = clean_and_tokenize(message)
                for word in words:
                    if word and word not in stop_words:
                        word_freq[word] += 1
            most_used_word = max(word_freq.items(), key=lambda x: x[1], default=('N/A', 0))[0]

            participant_data.append({
                'name': name,
                'message_count': message_count,
                'avg_messages_per_day': avg_messages_per_day,
                'most_used_word': most_used_word if most_used_word != 'N/A' else 'N/A',
                'avg_words_per_day': avg_words_per_day,
            })

        # Sort participants by message_count in descending order
        participant_data.sort(key=lambda x: x['message_count'], reverse=True)

        logger.debug(f"Participant data: {participant_data}")

        # Store the data in the session, including the chat name
        request.session['stats'] = stats
        request.session['participants'] = participant_data
        request.session['chat_name'] = chat_name
        logger.debug(f"Chat name stored in session: {chat_name}")

        # Clean up the file
        os.remove(file_path)

        return redirect('results')
    return render(request, 'mos3c/upload.html')

def results(request):
    # Check if session data exists
    if 'stats' not in request.session or 'participants' not in request.session:
        return redirect('upload')  # Redirect to upload page if no data

    # Retrieve data from the session
    stats = request.session.get('stats', {
        'total_messages': 0,
        'users_messages': 0,
        'avg_messages_per_day': 0,
    })
    participants = request.session.get('participants', [])
    chat_name = request.session.get('chat_name', 'Unknown Chat')
    logger.debug(f"Chat name retrieved in results view: {chat_name}")

    # Clear the session data to avoid keeping it around
    request.session.pop('stats', None)
    request.session.pop('participants', None)
    request.session.pop('chat_name', None)

    return render(request, 'mos3c/results.html', {
        'stats': stats,
        'participants': participants,
        'chat_name': chat_name,
    })

def clean_and_tokenize(text):
    # Remove "<Media omitted>" and similar placeholders
    if "<Media omitted>" in text or "<This message was edited>" in text:
        return []
    # Remove punctuation and numbers
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    text = re.sub(r'\d+', '', text)  # Remove numbers
    # Convert to lowercase
    text = text.lower()
    # Split into words
    words = text.split()
    # Remove emojis (basic approach; for a more robust solution, use an emoji library like `emoji`)
    words = [word for word in words if not any(ord(char) > 127 for char in word)]
    return words