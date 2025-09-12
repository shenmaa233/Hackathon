import subprocess

class ToolController:
    def run_scientific_tool(self, tool_name: str, args: list[str]) -> str:
        """
        This is a placeholder for running scientific tools.
        In a real application, you would have more sophisticated logic
        for managing different tools and their environments.
        """
        try:
            result = subprocess.run(
                [tool_name] + args,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout
        except FileNotFoundError:
            return f"Error: Tool '{tool_name}' not found."
        except subprocess.CalledProcessError as e:
            return f"Error executing tool '{tool_name}':\n{e.stderr}"

