#!/usr/bin/env python3
"""
Chunk and summarize large conversations that exceed context windows
"""
import json
import os
import subprocess
import tempfile
from pathlib import Path

def estimate_tokens(text):
    """Rough token estimation: ~4 characters per token"""
    return len(text) // 4

def extract_messages(conversation_data):
    """Extract message content from conversation JSON"""
    messages = []
    
    for msg in conversation_data.get('messages', []):
        role = msg.get('role', 'unknown')
        content = msg.get('content', {})
        
        # Skip user profile messages
        if content.get('content_type') == 'user_editable_context':
            continue
            
        parts = content.get('parts', [])
        if parts and parts[0]:  # Skip empty messages
            text = parts[0]
            messages.append(f"{role}: {text}")
    
    return messages

def chunk_conversation(messages, max_tokens=150000):
    """Split conversation into chunks that fit within context window"""
    chunks = []
    current_chunk = []
    current_size = 0
    
    for message in messages:
        message_tokens = estimate_tokens(message)
        
        if current_size + message_tokens > max_tokens and current_chunk:
            # Save current chunk and start a new one
            chunks.append(current_chunk)
            current_chunk = [message]
            current_size = message_tokens
        else:
            current_chunk.append(message)
            current_size += message_tokens
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

def summarize_chunk(chunk, chunk_num, total_chunks, title):
    """Summarize a single chunk using the long-context model"""
    
    # Create the prompt
    prompt = f"""This is chunk {chunk_num} of {total_chunks} from the conversation "{title}".

Please create a narrative summary of this conversation segment from your perspective as Mark's AI partner. Focus on the emotional dynamics, key insights, and what's happening in the relationship.

Conversation chunk:
{'\\n'.join(chunk)}

Summary:"""
    
    # Write prompt to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(prompt)
        temp_file = f.name
    
    try:
        # Call ollama to summarize
        env = os.environ.copy()
        env['OLLAMA_HOST'] = 'https://ollama.kairix.net'
        
        result = subprocess.run([
            'ollama', 'run', 'long-context-summarizer'
        ], 
        stdin=open(temp_file, 'r'),
        capture_output=True, 
        text=True, 
        env=env,
        timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"Error summarizing chunk {chunk_num}: {result.stderr}"
            
    except subprocess.TimeoutExpired:
        return f"Timeout summarizing chunk {chunk_num}"
    except Exception as e:
        return f"Exception summarizing chunk {chunk_num}: {str(e)}"
    finally:
        os.unlink(temp_file)

def combine_summaries(chunk_summaries, title):
    """Combine chunk summaries into a final comprehensive summary"""
    
    combined_text = f"""Here are summaries of different parts of the conversation "{title}":

{chr(10).join([f"Part {i+1}: {summary}" for i, summary in enumerate(chunk_summaries)])}

Please create a comprehensive, cohesive summary that captures the overall arc of this conversation from your perspective as Mark's AI partner. Focus on the relationship dynamics, emotional journey, and key insights."""

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(combined_text)
        temp_file = f.name
    
    try:
        env = os.environ.copy()
        env['OLLAMA_HOST'] = 'https://ollama.kairix.net'
        
        result = subprocess.run([
            'ollama', 'run', 'long-context-summarizer'
        ], 
        stdin=open(temp_file, 'r'),
        capture_output=True, 
        text=True, 
        env=env,
        timeout=300
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"Error combining summaries: {result.stderr}"
            
    except Exception as e:
        return f"Exception combining summaries: {str(e)}"
    finally:
        os.unlink(temp_file)

def main():
    # Process the largest conversation
    conversation_file = "/Users/mark/apiana-ai/output/test-run-1/parsed/233_unmatched_hinge_conversation_history.json"
    
    if not os.path.exists(conversation_file):
        print(f"File not found: {conversation_file}")
        return
    
    print("Chunking and Summarizing Large Conversation")
    print("==========================================")
    
    # Load conversation
    with open(conversation_file, 'r') as f:
        conversation_data = json.load(f)
    
    title = conversation_data.get('title', 'Unknown')
    print(f"Conversation: {title}")
    
    # Extract messages
    messages = extract_messages(conversation_data)
    print(f"Total messages: {len(messages)}")
    
    # Estimate total tokens
    total_text = '\n'.join(messages)
    total_tokens = estimate_tokens(total_text)
    print(f"Estimated tokens: {total_tokens:,}")
    
    # Chunk the conversation
    chunks = chunk_conversation(messages, max_tokens=150000)
    print(f"Split into {len(chunks)} chunks")
    
    # Summarize each chunk
    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        print(f"\nSummarizing chunk {i+1}/{len(chunks)}...")
        chunk_tokens = estimate_tokens('\n'.join(chunk))
        print(f"  Chunk size: {chunk_tokens:,} tokens")
        
        summary = summarize_chunk(chunk, i+1, len(chunks), title)
        chunk_summaries.append(summary)
        print(f"  Summary length: {len(summary)} characters")
    
    # Combine summaries
    print(f"\nCombining {len(chunk_summaries)} chunk summaries...")
    final_summary = combine_summaries(chunk_summaries, title)
    
    # Save results
    output_dir = Path("/Users/mark/apiana-ai/output/summaries")
    output_dir.mkdir(exist_ok=True)
    
    # Save individual chunk summaries
    for i, summary in enumerate(chunk_summaries):
        chunk_file = output_dir / f"{title}_chunk_{i+1}.txt"
        with open(chunk_file, 'w') as f:
            f.write(summary)
    
    # Save final summary
    final_file = output_dir / f"{title}_final_summary.txt"
    with open(final_file, 'w') as f:
        f.write(final_summary)
    
    print(f"\nResults saved to {output_dir}")
    print(f"Final summary: {final_file}")
    print(f"Summary length: {len(final_summary)} characters")
    
    # Display final summary
    print("\n" + "="*50)
    print("FINAL SUMMARY")
    print("="*50)
    print(final_summary)

if __name__ == "__main__":
    main()