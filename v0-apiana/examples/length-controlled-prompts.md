# Length-Controlled Prompting Examples

## 1. Explicit Length Instructions

**Short Response:**
```
"Explain quantum computing in exactly 2 sentences."
```

**Medium Response:**
```
"Explain quantum computing in approximately 150 words. Be concise but complete."
```

**Structured Response:**
```
"Explain quantum computing using exactly 3 bullet points, each 1-2 sentences long."
```

## 2. Format Constraints

**List Format:**
```
"List the top 5 benefits of exercise. Use this format:
1. Benefit: Explanation (max 20 words)
2. Benefit: Explanation (max 20 words)"
```

**Paragraph Limit:**
```
"Explain Python in exactly 2 paragraphs. First paragraph: what it is. Second paragraph: why it's useful."
```

## 3. Stop Sequences

**Natural Endings:**
```json
{
  "stop": [
    "In conclusion",
    "To summarize", 
    "Finally",
    "\n\n---",
    "That concludes"
  ]
}
```

**Format-Based:**
```json
{
  "stop": [
    "\n\n",           // Stop at double newline
    "\n#",            // Stop at markdown headers
    "\n1.",           // Stop at numbered lists
    "```"             // Stop at code blocks
  ]
}
```

## 4. System Prompts for Length Control

**Concise Assistant:**
```
"You are a concise AI assistant. Always provide complete but brief answers. Aim for 2-3 sentences unless more detail is specifically requested."
```

**Structured Assistant:**
```
"You are a structured AI assistant. Always organize your responses with clear headings and bullet points. Keep each section brief."
```