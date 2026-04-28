"""Chapter writing API endpoints with SSE streaming."""

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.utils.sse_helpers import check_disconnected, create_sse_sender

router = APIRouter(prefix="/api/chapters", tags=["chapters"])


class ChapterWriteRequest(BaseModel):
    project: str
    volume: int = 1
    chapter: int = 1
    instruction: str = ""
    mode: str = "interactive"  # interactive or auto


class ChapterFeedbackRequest(BaseModel):
    project: str
    volume: int
    chapter: int
    action: str  # "confirm" or "modify"
    feedback: str = ""


class ChapterQueryRequest(BaseModel):
    project: str
    query: str


@router.get("/{project}/volume/{volume}")
async def list_chapters(request: Request, project: str, volume: int):
    chaps = request.app.state.fm.list_chapters(project, volume)
    return {"chapters": chaps}


@router.get("/{project}/volume/{volume}/chapter/{chapter}")
async def get_chapter(request: Request, project: str, volume: int, chapter: int):
    content = request.app.state.fm.read_chapter(project, volume, chapter)
    return {"content": content or "", "volume": volume, "chapter": chapter}


@router.post("/generate")
async def generate_chapter(request: Request, body: ChapterWriteRequest):
    """Generate chapter with SSE streaming for interactive flow.

    Returns SSE events: status, outline, text_chunk, text_complete, sync_summary, done
    """
    llm = request.app.state.llm
    fm = request.app.state.fm

    async def event_stream():
        from app.skills.outline import run as outline_run
        from app.skills.chapter_write import run as chapter_run
        from app.skills.knowledge_sync import run as sync_run
        from app.skills.writing_assist import run as assist_run

        project = body.project
        volume = body.volume
        chapter = body.chapter

        send = create_sse_sender()

        try:
            fm.ensure_volume_dir(project, volume)

            # Validate that book outline and volume outline exist
            book_outline = fm.read_book_outline(project)
            if not book_outline:
                yield send("error", {
                    "message": "尚未创建全书大纲。请先前往「大纲管理」生成全书大纲和第" + str(volume) + "卷大纲，再开始章节写作。",
                    "code": "MISSING_BOOK_OUTLINE"
                })
                return

            vol_outline = fm.read_volume_outline(project, volume)
            if not vol_outline:
                yield send("error", {
                    "message": "尚未创建第" + str(volume) + "卷大纲。请先前往「大纲管理」生成第" + str(volume) + "卷大纲，再开始章节写作。",
                    "code": "MISSING_VOLUME_OUTLINE"
                })
                return

            # Step 1: Generate chapter outline with streaming
            if await check_disconnected(request):
                return
            yield send("status", {"message": "正在生成章节大纲..."})

            existing_outline = fm.read_chapter_outline(project, volume, chapter)
            outline_stream = await outline_run(llm, fm, project, {
                "action": "create_chapter",
                "volume": volume,
                "chapter": chapter,
                "instruction": body.instruction,
                "existing_chapter_outline": existing_outline,
                "stream": True,
            })

            # Stream outline chunks to frontend (filter reasoning, only show content)
            if isinstance(outline_stream, dict):
                yield send("error", {"message": outline_stream.get("error", "大纲生成失败")})
                return

            outline_content = ""
            chunk_count = 0
            reasoning_count = 0
            async for chunk_type, chunk_text in outline_stream:
                if chunk_type == "reasoning":
                    if reasoning_count == 0:
                        yield send("status", {"message": "模型思考中..."})
                    reasoning_count += 1
                    continue
                outline_content += chunk_text
                yield send("outline_chunk", {"text": chunk_text})
                chunk_count += 1
                if chunk_count % 5 == 0 and await check_disconnected(request):
                    return

            fm.write_chapter_outline(project, volume, chapter, outline_content)
            yield send("outline", {"markdown": outline_content})

            # Step 2: Wait for user confirmation or feedback
            # For interactive mode, pause here. The frontend will call the feedback endpoint.
            # For auto mode, continue directly.
            if body.mode == "interactive":
                yield send("awaiting_confirmation", {"message": "请确认大纲，或提供修改意见"})
                # Store outline for feedback endpoint
                return

            # Auto mode: proceed directly
            yield send("status", {"message": "开始生成正文..."})

            # Step 3: Pre-write check (writing assistant)
            hints = await assist_run(llm, fm, project, {
                "action": "pre_write_check",
                "volume": volume,
                "chapter": chapter,
            })
            if hints.get("success"):
                yield send("hints", {"data": hints.get("result", {})})

            # Step 4: Generate chapter text with streaming
            if await check_disconnected(request):
                return
            stream = await chapter_run(llm, fm, project, {
                "action": "write",
                "volume": volume,
                "chapter": chapter,
                "instruction": body.instruction,
                "stream": True,
            })

            full_text = ""
            chunk_count = 0
            reasoning_count = 0
            if isinstance(stream, dict):
                yield send("error", {"message": stream.get("error", "正文生成失败")})
                return
            async for chunk_type, chunk_text in stream:
                if chunk_type == "reasoning":
                    if reasoning_count == 0:
                        yield send("status", {"message": "模型思考中..."})
                    reasoning_count += 1
                    continue
                full_text += chunk_text
                yield send("text_chunk", {"text": chunk_text})
                chunk_count += 1
                if chunk_count % 10 == 0 and await check_disconnected(request):
                    return

            fm.write_chapter(project, volume, chapter, full_text)
            yield send("text_complete", {"full_text": full_text})

            # Step 5: Knowledge sync
            if await check_disconnected(request):
                return
            yield send("status", {"message": "正在更新创作依据..."})
            async for event in sync_run(llm, fm, project, {
                "action": "sync",
                "volume": volume,
                "chapter": chapter,
                "chapter_content": full_text,
            }):
                if event["type"] == "progress":
                    yield send("status", {"message": event["message"]})
                elif event["type"] == "result":
                    sync_result = event["result"]
                    if sync_result.get("success"):
                        yield send("sync_summary", {"data": sync_result.get("result", {})})
                    else:
                        yield send("error", {"message": f"知识同步失败：{sync_result.get('error', '未知错误')}", "code": "SYNC_FAILED"})

            # Update project state
            state = fm.get_project_state(project)
            state["当前进度"]["当前章"] = chapter
            state["阶段"] = "正文创作"
            fm.save_project_state(project, state)

            yield send("done", {"message": "章节生成完成"})

        except Exception as e:
            yield send("error", {"message": str(e)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/feedback")
async def chapter_feedback(request: Request, body: ChapterFeedbackRequest):
    """Handle user feedback on chapter outline or content."""
    llm = request.app.state.llm
    fm = request.app.state.fm

    async def event_stream():
        from app.skills.outline import run as outline_run
        from app.skills.chapter_write import run as chapter_run
        from app.skills.knowledge_sync import run as sync_run
        from app.skills.writing_assist import run as assist_run

        project = body.project
        volume = body.volume
        chapter = body.chapter

        send = create_sse_sender()

        try:
            if body.action == "modify":
                # Adjust outline based on feedback
                if await check_disconnected(request):
                    return
                yield send("status", {"message": "正在根据反馈调整大纲..."})
                outline_result = await outline_run(llm, fm, project, {
                    "action": "adjust_chapter",
                    "volume": volume,
                    "chapter": chapter,
                    "instruction": body.feedback,
                })

                if outline_result.get("success"):
                    outline_content = outline_result["content"]
                    fm.write_chapter_outline(project, volume, chapter, outline_content)
                    yield send("outline", {"markdown": outline_content, "adjusted": True})
                else:
                    yield send("error", {"message": outline_result.get("error", "大纲调整失败")})
                    return

            elif body.action == "confirm":
                # Proceed to generate chapter text
                if await check_disconnected(request):
                    return
                yield send("status", {"message": "开始生成正文..."})

                # Pre-write check
                hints = await assist_run(llm, fm, project, {
                    "action": "pre_write_check",
                    "volume": volume,
                    "chapter": chapter,
                })
                if hints.get("success"):
                    yield send("hints", {"data": hints.get("result", {})})

                # Generate chapter text with streaming
                if await check_disconnected(request):
                    return
                stream_result = await chapter_run(llm, fm, project, {
                    "action": "write",
                    "volume": volume,
                    "chapter": chapter,
                    "stream": True,
                })

                full_text = ""
                chunk_count = 0
                reasoning_count = 0
                if isinstance(stream_result, dict):
                    yield send("error", {"message": stream_result.get("error", "正文生成失败")})
                    return
                async for chunk_type, chunk_text in stream_result:
                    if chunk_type == "reasoning":
                        reasoning_count += 1
                        if reasoning_count % 10 == 0:
                            yield send("status", {"message": "模型思考中..."})
                        continue
                    full_text += chunk_text
                    yield send("text_chunk", {"text": chunk_text})
                    chunk_count += 1
                    if chunk_count % 10 == 0 and await check_disconnected(request):
                        return

                fm.write_chapter(project, volume, chapter, full_text)
                yield send("text_complete", {"full_text": full_text})

                # Knowledge sync
                if await check_disconnected(request):
                    return
                yield send("status", {"message": "正在更新创作依据..."})
                async for event in sync_run(llm, fm, project, {
                    "action": "sync",
                    "volume": volume,
                    "chapter": chapter,
                    "chapter_content": full_text,
                }):
                    if event["type"] == "progress":
                        yield send("status", {"message": event["message"]})
                    elif event["type"] == "result":
                        sync_result = event["result"]
                        if sync_result.get("success"):
                            yield send("sync_summary", {"data": sync_result.get("result", {})})
                        else:
                            yield send("error", {"message": f"知识同步失败：{sync_result.get('error', '未知错误')}", "code": "SYNC_FAILED"})

                # Update project state
                state = fm.get_project_state(project)
                state["当前进度"]["当前章"] = chapter
                state["阶段"] = "正文创作"
                fm.save_project_state(project, state)

                yield send("done", {"message": "章节生成完成"})

            else:
                yield send("error", {"message": f"Unknown action: {body.action}"})

        except Exception as e:
            yield send("error", {"message": str(e)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/query")
async def query_memory(request: Request, body: ChapterQueryRequest):
    """Query project memory for information."""
    from app.skills.writing_assist import run as assist_run
    llm = request.app.state.llm
    fm = request.app.state.fm
    result = await assist_run(llm, fm, body.project, {
        "action": "memory_search",
        "query": body.query,
    })
    return result


@router.get("/{project}/foreshadowing")
async def get_foreshadowing(request: Request, project: str):
    content = request.app.state.fm.read_foreshadowing_list(project)
    return {"content": content or ""}
