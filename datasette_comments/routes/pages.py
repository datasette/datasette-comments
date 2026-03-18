from datasette import Response

from ..router import router, check_permission


@router.GET(r"^/-/datasette-comments/activity$")
@check_permission()
async def activity_view(datasette=None, request=None):
    return Response.html(
        await datasette.render_template(
            "activity_view.html",
            {
                "entrypoint": "src/pages/activity/index.tsx",
            },
            request=request,
        )
    )
