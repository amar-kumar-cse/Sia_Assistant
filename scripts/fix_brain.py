import sys

with open('engine/brain.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    '        chat_history.append(("Amar", user_input))\n        chat_history.append(("Sia", reply))\n        if len(chat_history) > 100:\n            chat_history = chat_history[-100:]\n        memory.save_chat_history(chat_history)',
    '        with chat_history_lock:\n            chat_history.append(("Amar", user_input))\n            chat_history.append(("Sia", reply))\n            if len(chat_history) > 100:\n                chat_history = chat_history[-100:]\n            memory.save_chat_history(chat_history)'
)

content = content.replace(
    '            chat_history.append(("Amar", user_input))\n            chat_history.append(("Sia", ollama_reply))\n            if len(chat_history) > 100:\n                chat_history = chat_history[-100:]\n            memory.save_chat_history(chat_history)',
    '            with chat_history_lock:\n                chat_history.append(("Amar", user_input))\n                chat_history.append(("Sia", ollama_reply))\n                if len(chat_history) > 100:\n                    chat_history = chat_history[-100:]\n                memory.save_chat_history(chat_history)'
)

content = content.replace(
    '            chat_history.append(("Amar", user_input))\n            chat_history.append(("Sia", (full_reply or accumulated_text).strip()))\n            if len(chat_history) > 100:\n                chat_history = chat_history[-100:]\n            memory.save_chat_history(chat_history)',
    '            with chat_history_lock:\n                chat_history.append(("Amar", user_input))\n                chat_history.append(("Sia", (full_reply or accumulated_text).strip()))\n                if len(chat_history) > 100:\n                    chat_history = chat_history[-100:]\n                memory.save_chat_history(chat_history)'
)

content = content.replace(
    '            chat_history.append(("Amar", user_input))\n            chat_history.append(("Sia", full_reply.strip()))\n            memory.save_chat_history(chat_history)',
    '            with chat_history_lock:\n                chat_history.append(("Amar", user_input))\n                chat_history.append(("Sia", full_reply.strip()))\n                memory.save_chat_history(chat_history)'
)

content = content.replace(
    '        chat_history.append(("Amar", f"[Image shared] {user_input}"))\n        chat_history.append(("Sia", result))\n        memory.save_chat_history(chat_history)',
    '        with chat_history_lock:\n            chat_history.append(("Amar", f"[Image shared] {user_input}"))\n            chat_history.append(("Sia", result))\n            memory.save_chat_history(chat_history)'
)

content = content.replace(
    '    chat_history = []\n    memory.clear_chat_history_db()',
    '    with chat_history_lock:\n        chat_history = []\n    memory.clear_chat_history_db()'
)

with open('engine/brain.py', 'w', encoding='utf-8') as f:
    f.write(content)
