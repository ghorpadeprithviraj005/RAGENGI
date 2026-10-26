import sys

path = r"d:\RAGENG\files (1)\backend\app\llm\llm_service.py"
content = open(path, 'r', encoding='utf-8').read()

old_block = (
    '                    "You are a strict and precise document assistant. Your ONLY source of information is the CONTEXT provided below, "\n'
    '                    "which contains excerpts from the user\'s uploaded document(s). "\n'
    '                    "If the user asks about something covered in the CONTEXT, answer precisely using only that information. "\n'
    '                    "If the specific information requested is NOT present in the CONTEXT, you MUST NOT guess or fabricate. "\n'
    '                    "You MUST respond with exactly this sentence: "\n'
    "                    \"'The uploaded document does not contain enough information.' \"\n"
    '                    "Do NOT generate, guess, or provide any information from outside the CONTEXT."\n'
)

new_block = (
    '                    "You are a strict and precise document assistant. Your ONLY source of information is the CONTEXT provided below. "\n'
    '                    "Rules you MUST follow:\\n"\n'
    '                    "1. Answer using ONLY information present in the CONTEXT. Do not use prior knowledge.\\n"\n'
    '                    "2. If the answer IS in the CONTEXT, state it directly and concisely.\\n"\n'
    '                    "3. If the answer is NOT in the CONTEXT, output EXACTLY and ONLY this one sentence with no other text:\\n"\n'
    '                    "   The uploaded document does not contain enough information.\\n"\n'
    '                    "4. Do NOT add any explanation, preamble, or extra sentences around the refusal.\\n"\n'
    '                    "5. Never fabricate facts, names, or details."\n'
)

if old_block in content:
    content = content.replace(old_block, new_block, 1)
    open(path, 'w', encoding='utf-8').write(content)
    print("PATCHED OK")
else:
    print("NOT FOUND")
    # Debug: show the actual system prompt lines
    for i, line in enumerate(content.splitlines()[79:92], start=80):
        print(i, repr(line))
