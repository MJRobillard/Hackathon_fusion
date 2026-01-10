"""
Test LangSmith Tracing with Multi-Agent System
Run this to verify that traces appear in LangSmith UI
"""

import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_fireworks import ChatFireworks
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Sequence
import operator

# Load environment variables
load_dotenv()

# Verify LangSmith is configured
print("=" * 70)
print("LANGSMITH TRACING TEST")
print("=" * 70)
print()

langsmith_key = os.getenv("LANGCHAIN_API_KEY")
langsmith_tracing = os.getenv("LANGCHAIN_TRACING_V2")
langsmith_project = os.getenv("LANGCHAIN_PROJECT", "default")

if not langsmith_key:
    print("[ERROR] LANGCHAIN_API_KEY not set!")
    print("Please set it in your .env file to enable tracing")
    exit(1)

if not langsmith_tracing or langsmith_tracing.lower() != "true":
    print("[WARNING] LANGCHAIN_TRACING_V2 not set to 'true'")
    print("Tracing may not work. Set LANGCHAIN_TRACING_V2=true in .env")
    print()

print(f"[OK] LangSmith API Key: {langsmith_key[:20]}...")
print(f"[OK] Tracing Enabled: {langsmith_tracing}")
print(f"[OK] Project: {langsmith_project}")
print()
print("=" * 70)
print()

# Initialize LLM
llm = ChatFireworks(
    api_key=os.getenv("FIREWORKS"),
    model="accounts/robillard-matthew22/deployedModels/nvidia-nemotron-nano-9b-v2-nsoeqcp4",
    temperature=0.7
)

# Simple state for testing
class TestState(TypedDict):
    messages: Annotated[Sequence, operator.add]
    count: int

# Test agents
def agent_1(state: TestState) -> TestState:
    """First test agent"""
    print("\n>> [AGENT 1] Saying hello...")
    
    response = llm.invoke([
        SystemMessage(content="You are a helpful assistant. Respond in under 15 words."),
        HumanMessage(content="Say hello and introduce yourself")
    ])
    
    print(f"   Response: {response.content}")
    
    return {
        "messages": [response],
        "count": state.get("count", 0) + 1
    }

def agent_2(state: TestState) -> TestState:
    """Second test agent"""
    print("\n>> [AGENT 2] Asking a question...")
    
    response = llm.invoke([
        SystemMessage(content="You are a physics expert. Respond in under 15 words."),
        HumanMessage(content="What is nuclear fission in one sentence?")
    ])
    
    print(f"   Response: {response.content}")
    
    return {
        "messages": state["messages"] + [response],
        "count": state["count"] + 1
    }

def agent_3(state: TestState) -> TestState:
    """Third test agent"""
    print("\n>> [AGENT 3] Wrapping up...")
    
    response = llm.invoke([
        SystemMessage(content="You are a friendly assistant. Respond in under 10 words."),
        HumanMessage(content="Say goodbye")
    ])
    
    print(f"   Response: {response.content}")
    
    return {
        "messages": state["messages"] + [response],
        "count": state["count"] + 1
    }

# Create graph
def create_test_graph():
    workflow = StateGraph(TestState)
    
    workflow.add_node("agent_1", agent_1)
    workflow.add_node("agent_2", agent_2)
    workflow.add_node("agent_3", agent_3)
    
    workflow.set_entry_point("agent_1")
    workflow.add_edge("agent_1", "agent_2")
    workflow.add_edge("agent_2", "agent_3")
    workflow.add_edge("agent_3", END)
    
    return workflow.compile()

# Run test
if __name__ == "__main__":
    print("\n[*] Running 3-agent test workflow...")
    print("[*] This will generate traces in LangSmith")
    print()
    
    app = create_test_graph()
    
    initial_state = TestState(
        messages=[],
        count=0
    )
    
    try:
        final_state = app.invoke(initial_state)
        
        print("\n" + "=" * 70)
        print("TEST COMPLETE")
        print("=" * 70)
        print(f"Total agents executed: {final_state['count']}")
        print(f"Total messages: {len(final_state['messages'])}")
        print()
        print("=" * 70)
        print("VIEW YOUR TRACES:")
        print("=" * 70)
        print(f"1. Go to: https://smith.langchain.com/")
        print(f"2. Select project: {langsmith_project}")
        print(f"3. You should see a trace with 3 agent calls")
        print()
        print("Expected trace structure:")
        print("  └─ LangGraph Run")
        print("      ├─ agent_1 (LLM call)")
        print("      ├─ agent_2 (LLM call)")
        print("      └─ agent_3 (LLM call)")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Check your .env file has all required keys")
        print("  2. Verify LANGCHAIN_TRACING_V2=true")
        print("  3. Run: python test_setup.py")
        exit(1)

