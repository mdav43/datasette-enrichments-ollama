from __future__ import annotations
from datasette_enrichments import Enrichment
from datasette import hookimpl
from datasette.database import Database
import httpx
from typing import List, Optional
from wtforms import (
    Form,
    StringField,
    TextAreaField,
    BooleanField,
    SelectField,
)
from wtforms.validators import ValidationError, DataRequired
import secrets
import sqlite_utils


@hookimpl
def register_enrichments():
    return [OllamaEnrichment()]


class OllamaEnrichment(Enrichment):
    name = "AI analysis using a ollama runnig service (macos/linux only)"
    slug = "ollama"
    description = "Analyze data using any of the models available in ollama (macos/linux only)"
    runs_in_process = True
    batch_size = 1

    async def get_config_form(self, datasette, db, table):
        columns = await db.table_columns(table)

        # Default template uses all string columns
        default = " ".join("{{ COL }}".replace("COL", col) for col in columns)

        url_columns = [col for col in columns if "url" in col.lower()]
        image_url_suggestion = ""
        if url_columns:
            image_url_suggestion = "{{ %s }}" % url_columns[0]

        class ConfigForm(Form):
            # Select box to pick model from those available on the local instance
            
            # cache the models available to speed up anything
            
            
            model = SelectField(
                "Model",
                choices=[
                    ("dolphin-phi:latest", "dolphin-phi:latest"),
                    ("another", "another"),
                ],
                default="dolphin-phi:latest",
            )
            prompt = TextAreaField(
                "Prompt",
                description="A template to run against each row to generate a prompt. Use {{ COL }} for columns.",
                default=default,
                validators=[DataRequired(message="Prompt is required.")],
                render_kw={"style": "height: 8em"},
            )
            image_url = StringField(
                "Image URL",
                description="Image URL template. Only used with gpt-4-vision.",
                default=image_url_suggestion,
            )
            system_prompt = TextAreaField(
                "System prompt",
                description="Instructions to apply to the main prompt. Can only be a static string, no {{ columns }}",
                default="",
            )
            json_format = BooleanField(
                "JSON object",
                description="Output a valid JSON object {...} instead of plain text",
                default=False,
            )
            output_column = StringField(
                "Output column name",
                description="The column to store the output in - will be created if it does not exist.",
                validators=[DataRequired(message="Column is required.")],
                default="prompt_output",
            )

            def validate_prompt(self, field):
                if (
                    self.json_format.data
                    and "json" not in field.data.lower()
                    and "json" not in self.system_prompt.data.lower()
                ):
                    raise ValidationError(
                        'The prompt or system prompt must contain the word "JSON" when JSON format is selected.'
                    )

        def stash_api_url(form, field):
            if not hasattr(datasette, "_enrichments_ollama_stashed_url"):
                datasette._enrichments_ollama_stashed_url = {}
            key = secrets.token_urlsafe(16)
            datasette._enrichments_ollama_stashed_url[key] = field.data
            field.data = key
        
        def get_available_models():
            # TODO: To be implemented so the models are auto populated
            
#             curl http://localhost:11434/api/tags 
#             {"models":[{"name":"codellama:latest","model":"codellama:latest","modified_at":"2024-02-09T10:40:41.498250553+08:00",
# "details":{"parent_model":"","format":"gguf","family":"llama","families":null,"parameter_size":"7B","quantization_level":"Q4_0"}},
# {"name":"dolphin-phi:latest","model":"dolphin-phi:latest","modified_at":"2024-02-12T22:16:04.986996096+08:00",
# "size":1602473850,"digest":"c5761fc772409945787240af89a5cce01dd39dc52f1b7b80d080a1163e8dbe10",
# "details":{"parent_model":"","format":"gguf","family":"phi2","families":["phi2"],
# "parameter_size":"3B","quantization_level":"Q4_0"}}]}%     
#               "size":3825910662,"digest":"8fdf8f752f6e80de33e82f381aba784c025982752cd1ae9377add66449d2225f",
            return None
        
        class ConfigFormWithKey(ConfigForm):
            api_url = StringField(
                "API url",
                description="Your Ollama url",
                validators=[
                    DataRequired(message="API url is required."),
                    stash_api_url,
                ],
            )

        plugin_config = datasette.plugin_config("datasette-enrichments-ollama") or {}
        api_url = plugin_config.get("api_url")

        return ConfigForm if api_url else ConfigFormWithKey

    async def initialize(self, datasette, db, table, config):
        # Ensure column exists
        output_column = config["output_column"]

        def add_column_if_not_exists(conn):
            db = sqlite_utils.Database(conn)
            if output_column not in db[table].columns_dict:
                db[table].add_column(output_column, str)

        await db.execute_write_fn(add_column_if_not_exists)

    async def _chat_completion(
        self, api_url, model, prompt, images, json_format=False
    ) -> str:
        
        # Parameters to ollama

        # model: (required) the model name
        # prompt: the prompt to generate a response for
        # images: (optional) a list of base64-encoded images (for multimodal models such as llava)
        # Advanced parameters (optional):

        # format: the format to return a response in. Currently the only accepted value is json
        # options: additional model parameters listed in the documentation for the Modelfile such as temperature
        # system: system message to (overrides what is defined in the Modelfile)
        # template: the prompt template to use (overrides what is defined in the Modelfile)
        # context: the context parameter returned from a previous request to /generate, this can be used to keep a short conversational memory
        # stream: if false the response will be returned as a single response object, rather than a stream of objects
        # raw: if true no formatting will be applied to the prompt. You may choose to use the raw parameter if you are specifying a full templated prompt in your request to the API
        # keep_alive: controls how long the model will stay loaded into memory following the request (default: 5m)

        body = {'model': model, 
                'prompt': prompt,
                'stream': False}
        
        async with httpx.AsyncClient() as client:
            print(body)
            
            response = await client.post(
                api_url,
                json=body,
                timeout=60.0,
            )
            print("phase 2")
            response.raise_for_status()
            print(response.json())
            result = str(response.json()["response"])
            print(result)
            print("Tried")
            # TODO: Record usage
            # usage = response["usage"]
            # completion_tokens, prompt_tokens
            return result

    async def ollama_completion(
        self, api_url, model, prompt, images, system=None, json_format=False
    ) -> str:
    
        return await self._chat_completion(
            api_url, model, prompt, images, json_format=json_format
        )

    async def enrich_batch(
        self,
        datasette: "Datasette",
        db: Database,
        table: str,
        rows: List[dict],
        pks: List[str],
        config: dict,
        job_id: int,
    ) -> List[Optional[str]]:
        # API url should be in plugin settings OR pointed to by config
        api_url = resolve_ollama_url(datasette, config)
        if rows:
            row = rows[0]
        else:
            return
        prompt = config["prompt"] or ""
        system = config["system_prompt"] or None
        json_format = bool(config.get("json_format"))
        output_column = config["output_column"]
        image_url = config["image_url"]
        for key, value in row.items():
            prompt = prompt.replace("{{ %s }}" % key, str(value or "")).replace(
                "{{%s}}" % key, str(value or "")
            )
            if image_url:
                image_url = image_url.replace(
                    "{{ %s }}" % key, str(value or "")
                ).replace("{{%s}}" % key, str(value or ""))
        model = config["model"]
        
        output = await self.ollama_completion(api_url, model, prompt, image_url, system, True)
        
        await db.execute_write(
            "update [{table}] set [{output_column}] = ? where {wheres}".format(
                table=table,
                output_column=output_column,
                wheres=" and ".join('"{}" = ?'.format(pk) for pk in pks),
            ),
            [output] + list(row[pk] for pk in pks),
        )


# The final response in the stream also includes additional data about the generation:

# total_duration: time spent generating the response
# load_duration: time spent in nanoseconds loading the model
# prompt_eval_count: number of tokens in the prompt
# prompt_eval_duration: time spent in nanoseconds evaluating the prompt
# eval_count: number of tokens the response
# eval_duration: time in nanoseconds spent generating the response
# context: an encoding of the conversation used in this response, this can be sent in the next request to keep a conversational memory
# response: empty if the response was streamed, if not streamed, this will contain the full response

class ApiUrlError(Exception):
    pass


## TODO
def get_available_models():
    url = "http://localhost:11434/api/tags"
    return None
    # plugin_config = datasette.plugin_config("datasette-enrichments-ollama") or {}
    # api_url = plugin_config.get("api_key")
    
    # response = requests.get(url)
    
    # if response.status_code == 200:
    #     return response.json()
    # else:
    #     print("Error:", response.status_code)
    #     return None

# def resolve_api_key(datasette, config):
#     plugin_config = datasette.plugin_config("datasette-enrichments-gpt") or {}
#     api_key = plugin_config.get("api_key")
#     if api_key:
#         return api_key
#     # Look for it in config
#     api_key_name = config.get("api_key")
#     if not api_key_name:
#         raise ApiUrlError("No API key reference found in config")
#     # Look it up in the stash
#     if not hasattr(datasette, "_enrichments_ollama_stashed_url"):
#         raise ApiUrlError("No API key stash found")
#     stashed_keys = datasette._enrichments_ollama_stashed_url
#     if api_key_name not in stashed_keys:
#         raise ApiUrlError("No API key found in stash for {}".format(api_key_name))
#     return stashed_keys[api_key_name]

def resolve_ollama_url(datasette, config):
    plugin_config = datasette.plugin_config("datasette-enrichments-ollama") or {}
    api_url = plugin_config.get("api_url")
    if api_url:
        return api_url
    # Look for it in config
    api_url_name = config.get("api_url")
    if not api_url_name:
        raise ApiUrlError("No API URL found in config")
    # Look it up in the stash
    if not hasattr(datasette, "_enrichments_ollama_stashed_url"):
        raise ApiUrlError("No API Url stash found")
    stashed_url = datasette._enrichments_ollama_stashed_url
    if api_url_name not in stashed_url:
        raise ApiUrlError("No API url found in stash for {}".format(api_url_name))
    return stashed_url[api_url_name]
