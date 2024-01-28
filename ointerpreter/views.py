import json

from django.http import JsonResponse
from django.views import View

from ointerpreter.ointerpreter_engine import get_interpreter_result


class CodeInterpreterView(View):
    """
    This view handles giving queries and tasks to code interpreter. It does not interact with the database directly,
    hence does not use a serializer_class. Instead, it relies on custom utility functions.
    """

    serializer_class = None

    async def post(self, request):
        try:
            data = json.loads(request.body)
            query = data.get("query")
            final_response = await get_interpreter_result(query)
            return JsonResponse({"success": "Process Done", "data": final_response})
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
