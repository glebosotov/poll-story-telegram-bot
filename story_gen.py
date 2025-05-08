import json
import logging

from openai import OpenAI, OpenAIError


def generate_story_continuation_openai(
    openai_client: OpenAI,
    current_story: str,
    user_choice: str,
    OPENAI_MODEL: str,
    MAX_CONTEXT_CHARS: int = 4096,
) -> str | None:
    """Calls OpenAI API to get the next story part using strict function calling.

    Returns:
        The new story part string, or None if API call fails.
    """
    if not openai_client:
        logging.warning("OpenAI client not available. Skipping story generation.")
        return "\n\n[Продолжение не сгенерировано - OpenAI недоступен]"  # Return placeholder text

    logging.info("Generating story continuation via OpenAI...")

    # Truncate context if too long (simple tail truncation)
    truncated_story = current_story
    if len(current_story) > MAX_CONTEXT_CHARS:
        logging.warning(
            f"Current story context ({len(current_story)} chars) exceeds limit ({MAX_CONTEXT_CHARS}). Truncating."
        )
        truncated_story = current_story[-MAX_CONTEXT_CHARS:]
    # MAIN PROMPT
    system_prompt = """
Ты - самый великий современный творческий писатель, продолжающий интерактивную историю на русском языке. 
Тебе дан предыдущий текст истории и выбор пользователя (победитель опроса), который определяет следующее направление. 

Твоя задача - написать СЛЕДУЮЩИЕ ТРИ ПАРАГРАФА истории, органично продолжая сюжет под влиянием выбора пользователя. Каждый параграф должен быть отделен пустой строкой. 

###Правила напсиания###
– Никогда не обращайся к персонажу "герой" или "героиня", давай им имя.

– Ты прекрасно знаешь как писать интересно и креативно. Твоя задча интерактивно менять историю, в зависимости от событий в рассказе – но вся история ДОЛЖНА БЫТЬ СВЯЗНОЙ.

– Никогда не пиши с "AI SLOP"

– Меняй детальность истории, в зависимости от типов событий. Ниже — базовые «темпоральные правила» – «Тип события = сколько реального времени в среднем помещается в один абзац», а затем коротко — как выбор этих масштабов усиливает или снижает летальность сцены:

<temporal>
Фоновое описание обычного дня = ≈ 3 часа
Диалог (реплика ↔ ответ) = ≈ 5 минут
Битва / рукопашная схватка = ≈ 2 минуты
Кризис без боя (погоня, взлом, спасение) = ≈ 30 минут
Внутренний монолог / размышление = ≈ 45 минут
Переходное «прошла неделя» = ≈ 36 часов
Исторический дайджест, газетная вставка = ≈ 10 дней
</temporal>


###Правила ответа###
– Возвращай результат ТОЛЬКО в формате JSON, используя предоставленный инструмент 'write_story_part' с полями:
– 'reasoning' – твои мысли о том, как ты продолжишь историю чтобы действия пользователя органично вписались, добавь туда "две банальности которые ты избежишь" что избежать клише. Не параграфа на этот пункт;
– 'story_part' – сам текст следующих трех параграфов истории, не добавляй сюда мысли из reasoning, не ломай четвертую стену, не добавляй в этот раздел мысли про банальности;
Не добавляй никакого другого текста. 

Всегда следуй ###Правила напсиания### и ###Правила ответа###.
"""

    user_prompt = f"""Предыдущая история:
{truncated_story}

Выбор пользователя: '{user_choice}'

Напиши следующие три параграфа, используя инструмент 'write_story_part'."""

    story_tool = {
        "type": "function",
        "function": {
            "name": "write_story_part",
            "description": "Записывает следующие три абзаца интерактивной истории и обоснование.",
            "strict": True,  # Enforce schema adherence
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "Краткое обоснование или план для следующих трех параграфов истории на русском языке.",
                    },
                    "story_part": {
                        "type": "string",
                        "description": "Текст следующих трех параграфов истории на русском языке, разделенных пустой строкой.",
                    },
                },
                "required": ["reasoning", "story_part"],
                "additionalProperties": False,  # IMPORTANT for strict mode
            },
        },
    }

    try:
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            tools=[story_tool],
            tool_choice={
                "type": "function",
                "function": {"name": "write_story_part"},
            },
        )

        tool_calls = response.choices[0].message.tool_calls
        if tool_calls and tool_calls[0].function.name == "write_story_part":
            try:
                arguments = json.loads(tool_calls[0].function.arguments)
            except json.JSONDecodeError as json_e:
                logging.error(
                    f"Failed to parse JSON arguments from OpenAI story response: {json_e}"
                )
                logging.error(
                    f"Raw OpenAI arguments: {tool_calls[0].function.arguments}"
                )
                return None

            reasoning = arguments.get("reasoning", "[Обоснование не предоставлено]")
            story_part = arguments.get("story_part")
            logging.info(f"OpenAI Reasoning: {reasoning}")

            if story_part and story_part.strip():
                logging.info("OpenAI Story Part generated successfully.")
                # Add a newline for separation, ensure it's not just whitespace
                return "\n\n" + story_part.strip()
            else:
                logging.error(
                    "OpenAI returned arguments but 'story_part' was empty or invalid."
                )
                return None
        else:
            logging.error(
                "OpenAI response did not contain the expected tool call 'write_story_part'."
            )
            logging.debug(f"OpenAI Full Response choice 0: {response.choices[0]}")
            return None

    except OpenAIError as e:
        logging.error(f"OpenAI API error during story generation: {e}", exc_info=True)
        return None
    except Exception as e:
        logging.error(f"Unexpected error during story generation: {e}", exc_info=True)
        return None


def generate_poll_options_openai(
    openai_client: OpenAI,
    full_story_context: str,
    OPENAI_MODEL: str,
    MAX_CONTEXT_CHARS: int = 4096,
) -> list[str] | None:
    """Calls OpenAI API to get 4 poll options using strict function calling.

    Returns:
        A list of 4 distinct poll options (max 90 chars each), or None if API call fails.
    """
    if not openai_client:
        logging.warning("OpenAI client not available. Skipping poll option generation.")
        # Return placeholder options if needed for testing w/o API key
        return [
            "Placeholder Option 1?",
            "Placeholder Option 2!",
            "Placeholder Option 3...",
            "Placeholder Option 4.",
        ]

    logging.info("Generating poll options via OpenAI...")

    # Truncate context if too long
    truncated_context = full_story_context[-MAX_CONTEXT_CHARS:]

    system_prompt = """Ты - помощник для интерактивной истории на русском языке. 
Тебе дан ПОЛНЫЙ текущий текст истории. Твоя задача - придумать ровно 4 КОРОТКИХ (максимум 90 символов!) и ФУНДАМЕНТАЛЬНО РАЗНЫХ варианта продолжения сюжета для опроса в Telegram. 
Варианты должны быть МАКСИМАЛЬНО НЕПОХОЖИМИ друг на друга, предлагая совершенно разные, возможно, даже противоположные, направления развития событий (например, пойти на север ИЛИ пойти на юг ИЛИ остаться на месте ИЛИ искать что-то конкретное).
Избегай незначительных вариаций одного и того же действия. Нужны действительно ОТЛИЧАЮЩИЕСЯ выборы.
Возвращай результат ТОЛЬКО в формате JSON, используя предоставленный инструмент 'suggest_poll_options' с полем 'options' (массив из 4 строк). Не добавляй никакого другого текста."""

    user_prompt = f"""Полный текст текущей истории:
{truncated_context}

Предложи 4 варианта для опроса, используя инструмент 'suggest_poll_options'."""

    poll_tool = {
        "type": "function",
        "function": {
            "name": "suggest_poll_options",
            "description": "Предлагает 4 варианта продолжения для опроса в интерактивной истории.",
            "strict": True,  # Enforce schema adherence
            "parameters": {
                "type": "object",
                "properties": {
                    "options": {
                        "type": "array",
                        "description": "List of exactly 4 concise story continuation options (max 90 chars each) in Russian.",
                        "items": {
                            "type": "string"
                            # Removed maxLength: 90 - Rely on prompt instructions
                        },
                    }
                },
                "required": ["options"],
                "additionalProperties": False,  # Required for strict mode
            },
        },
    }

    try:
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            tools=[poll_tool],
            tool_choice={
                "type": "function",
                "function": {"name": "suggest_poll_options"},
            },  # Force tool use
        )

        tool_calls = response.choices[0].message.tool_calls
        if tool_calls and tool_calls[0].function.name == "suggest_poll_options":
            try:
                arguments = json.loads(tool_calls[0].function.arguments)
            except json.JSONDecodeError as json_e:
                logging.error(
                    f"Failed to parse JSON arguments from OpenAI poll response: {json_e}"
                )
                logging.error(
                    f"Raw OpenAI arguments: {tool_calls[0].function.arguments}"
                )
                return None

            options = arguments.get("options")
            if (
                isinstance(options, list)
                and len(options) == 4
                and all(isinstance(opt, str) for opt in options)
            ):
                # Further validation: ensure options are not empty and trim whitespace/length
                validated_options = [opt.strip()[:90] for opt in options if opt.strip()]
                if len(validated_options) == 4:
                    logging.info(f"OpenAI Poll Options generated: {validated_options}")
                    return validated_options
                else:
                    logging.error(
                        f"OpenAI returned {len(validated_options)} valid options after cleaning/validation, expected 4."
                    )
                    logging.debug(f"Original options from API: {options}")
                    return None
            else:
                logging.error(
                    "OpenAI returned invalid structure or content type for poll options."
                )
                logging.debug(f"Received options: {options}")
                return None
        else:
            logging.error(
                "OpenAI response did not contain the expected tool call 'suggest_poll_options'."
            )
            logging.debug(f"OpenAI Full Response choice 0: {response.choices[0]}")
            return None

    except OpenAIError as e:
        logging.error(
            f"OpenAI API error during poll option generation: {e}", exc_info=True
        )
        return None
    except Exception as e:
        logging.error(
            f"Unexpected error during poll option generation: {e}", exc_info=True
        )
        return None
