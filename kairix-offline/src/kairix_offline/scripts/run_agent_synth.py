import argparse
from kairix_offline.processing import synth_memories
import kairix_offline.ui as ui

parser = argparse.ArgumentParser(description='Process agent data')
parser.add_argument('agent_name' , help='Name of the agent')
parser.add_argument('run_id', help='ID of the run')

args = parser.parse_args()
synth_memories(args.agent_name, args.run_id)


