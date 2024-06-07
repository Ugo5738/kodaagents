import json

from autogenstudio import AgentWorkFlowConfig, AutoGenWorkFlowManager
from django.http import JsonResponse
from django.views import View

# load an agent specification in JSON
agent_spec = json.load(open("autogen/config/merged_config.json"))

# Create an AutoGen Workflow Configuration from the agent specification
agent_work_flow_config = FlowConfig(**agent_spec)

# Create a Workflow from the configuration
agent_work_flow = AutoGenWorkFlowManager(agent_work_flow_config)


# ============================> RESUME <============================
class AgencyView(View):
    """
    Run agent workflow
    """

    async def get(self, request, query):
        try:
            # to get autogen agent return value
            agent_work_flow.run(message=query)
            response = agent_work_flow.agent_history[-1]["message"]["content"]
            return JsonResponse(response)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
