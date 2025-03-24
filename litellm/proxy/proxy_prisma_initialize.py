import os
import json
from litellm.proxy.management_endpoints.model_management_endpoints import _add_models_to_db
from litellm.proxy._types import UserAPIKeyAuth
from litellm.types.router import Deployment, LiteLLM_Params, ModelInfo
from typing import List, Optional
from litellm.proxy.utils import PrismaClient
from litellm.proxy._types import LiteLLM_BudgetTable

SYSTEM_ID = os.environ.get("SYSTEM_ID")
DEFAULT_DATA_LOADED_SETTING_ID = "default_loaded"
default_models = [
    # OpenAI GPT models
    {
        "model_name": "openai/gpt-3.5-turbo",
        "litellm_params": {
            "model": "gpt-3.5-turbo",
            "custom_llm_provider": "openai",
            "api_key": os.environ.get("OPENAI_API_KEY"),
            "api_base": os.environ.get("OPENAI_API_BASE"),
        }
    },
    {
        "model_name": "openai/gpt-4",
        "litellm_params": {
            "model": "gpt-4",
            "custom_llm_provider": "openai",
            "api_key": os.environ.get("OPENAI_API_KEY"),
            "api_base": os.environ.get("OPENAI_API_BASE"),
        }
    },
    {
        "model_name": "openai/gpt-4-turbo",
        "litellm_params": {
            "model": "gpt-4-turbo",
            "custom_llm_provider": "openai",
            "api_key": os.environ.get("OPENAI_API_KEY"),
            "api_base": os.environ.get("OPENAI_API_BASE"),
        }
    },

    # Anthropic models (e.g., Claude)
    {
        "model_name": "anthropic/claude-3-7-sonnet-20250219",
        "litellm_params": {
            "model": "claude-3-7-sonnet-20250219",
            "custom_llm_provider": "anthropic",
            "api_key": os.environ.get("ANTHROPIC_API_KEY"),
            "api_base": os.environ.get("ANTHROPIC_API_BASE"),
        }
    },
    {
        "model_name": "anthropic/claude-3-5-haiku-20241022",
        "litellm_params": {
            "model": "claude-3-5-haiku-20241022",
            "custom_llm_provider": "anthropic",
            "api_key": os.environ.get("ANTHROPIC_API_KEY"),
            "api_base": os.environ.get("ANTHROPIC_API_BASE"),
        }
    },
    {
        "model_name": "anthropic/claude-3-5-sonnet-20241022",
        "litellm_params": {
            "model": "claude-3-5-sonnet-20241022",
            "custom_llm_provider": "anthropic",
            "api_key": os.environ.get("ANTHROPIC_API_KEY"),
            "api_base": os.environ.get("ANTHROPIC_API_BASE"),
        }
    },
    {
        "model_name": "anthropic/claude-3-5-sonnet-20240620",
        "litellm_params": {
            "model": "claude-3-5-sonnet-20240620",
            "custom_llm_provider": "anthropic",
            "api_key": os.environ.get("ANTHROPIC_API_KEY"),
            "api_base": os.environ.get("ANTHROPIC_API_BASE"),
        }
    },
    {
        # Expensive. Use judiciously
        "model_name": "anthropic/claude-3-opus-20240229",
        "litellm_params": {
            "model": "claude-3-opus-20240229",
            "custom_llm_provider": "anthropic",
            "api_key": os.environ.get("ANTHROPIC_API_KEY"),
            "api_base": os.environ.get("ANTHROPIC_API_BASE"),
        }
    },
    {
        "model_name": "anthropic/claude-3-sonnet-20240229",
        "litellm_params": {
            "model": "claude-3-sonnet-20240229",
            "custom_llm_provider": "anthropic",
            "api_key": os.environ.get("ANTHROPIC_API_KEY"),
            "api_base": os.environ.get("ANTHROPIC_API_BASE"),
        }
    },
    {
        "model_name": "anthropic/claude-3-haiku-20240307",
        "litellm_params": {
            "model": "claude-3-haiku-20240307",
            "custom_llm_provider": "anthropic",
            "api_key": os.environ.get("ANTHROPIC_API_KEY"),
            "api_base": os.environ.get("ANTHROPIC_API_BASE"),
        }
    }
]

async def initialize_defaults(prisma_client: Optional[PrismaClient]):
    if prisma_client is None:
        return

    try:
        if await are_default_settings_loaded(prisma_client):
            print("Default settings already loaded, skipping initialization.")
            return

        async with prisma_client.db._original_prisma.tx() as tx:
            budget_row = LiteLLM_BudgetTable()
            new_budget = prisma_client.jsonify_object(budget_row.json(exclude_none=True))
            _budget = await tx.litellm_budgettable.create(
                data={
                    **new_budget,  # type: ignore
                    "created_by": SYSTEM_ID,
                    "updated_by": SYSTEM_ID,
                }
            )  # type: ignore

            _organization = await tx.litellm_organizationtable.upsert(
                where={"organization_id": SYSTEM_ID},
                data={
                    "create": {
                        "organization_id": SYSTEM_ID,
                        "organization_alias": SYSTEM_ID,
                        "models": [],
                        "created_by": SYSTEM_ID,
                        "updated_by": SYSTEM_ID,
                        "budget_id": _budget.budget_id
                    },
                    "update": {}
                }
            )
            
            model_info = {
                "org_id": _organization.organization_id
            }
            
            deployment_models: List[Deployment] = [
                Deployment(
                    model_name=model["model_name"],
                    litellm_params=LiteLLM_Params(**model["litellm_params"]),
                    model_info=ModelInfo(**model_info)
                )
                for model in default_models
            ]

            model_responses = await _add_models_to_db(
                model_params_list=deployment_models, 
                user_api_key_dict=UserAPIKeyAuth(),
                prisma_client=prisma_client,
                transaction=tx
            )
            value = json.dumps({"value": True})
            await tx.litellm_config.upsert(
                where={"param_name": DEFAULT_DATA_LOADED_SETTING_ID},
                data={
                    "create": {
                        "param_name": DEFAULT_DATA_LOADED_SETTING_ID,
                        "param_value": value
                    },
                    "update": {
                        "param_value": value
                    }
                }
            )

        return model_responses

    except Exception as e:
        print(f"Error occurred while initializing defaults: {e}")
        raise

    
async def are_default_settings_loaded(prisma_client: PrismaClient) -> bool:
    default_settings = await prisma_client.db.litellm_config.find_first(
        where={"param_name": DEFAULT_DATA_LOADED_SETTING_ID}
    )
    if not default_settings:
        return False
    return bool(default_settings.param_value.get('value', False))
 