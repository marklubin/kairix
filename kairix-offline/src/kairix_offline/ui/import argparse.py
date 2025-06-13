import argparse
from kairix_offline.processing import synth_memories
import kairix_offline.ui as ui

def runjob(agent_name, job_id):
    """Run a job with the specified agent."""
    try:
        result = synth_memories(agent_name, job_id)
        print(result)
    except Exception as e:
        print(f"Error running job {job_id} for agent {agent_name}: {e}")
        raise

if __name__ == "__main__";
argument_parser = argparse.ArgumentParser(description="Run a job with the specified agent.")
argparse.add_argument("agent_name", type=str, help="Name of the agent to run the job with.")
argparse.add_argument("job_id", type=str, help="ID of the job to run.")

argument_parser.parse()



