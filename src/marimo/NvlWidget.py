import pathlib
from typing import Any, Dict, Optional

import anywidget
import traitlets
from neo4j import Driver, Result
from neo4j_viz.neo4j import from_neo4j


from neo4j_viz.gds import from_gds


_HERE = pathlib.Path(__file__).parent


class NvlWidget(anywidget.AnyWidget):
    """
    Anywidget wrapper around neo4j-viz (NVL).

    This widget takes a Neo4j query result (or executes a query via a Driver),
    converts it into a VisualizationGraph using `neo4j-viz.from_neo4j`, and
    renders the resulting HTML inside an iframe on the frontend.
    """

    # Front-end JavaScript lives in `nvl_widget.js` next to this file.
    _esm = _HERE.joinpath("nvl_widget.js")

    # HTML produced by neo4j-viz `VisualizationGraph.render()`
    html = traitlets.Unicode("").tag(sync=True)

    # Sizing options for the iframe
    width = traitlets.Unicode("100%").tag(sync=True)
    height = traitlets.Unicode("600px").tag(sync=True)

    @classmethod
    def from_result(
        cls,
        result: Result,
        *,
        width: str = "100%",
        height: str = "600px",
        render_kwargs: Optional[Dict[str, Any]] = None,
    ) -> "NvlWidget":
        """
        Create an NvlWidget from a `neo4j.Result` or `neo4j.graph.Graph`.

        Parameters
        ----------
        result:
            A Neo4j result object. For best results, use `Result.graph`
            as a transformer when executing the query.
        width, height:
            CSS-compatible width/height passed to the iframe (e.g. '100%', '800px').
        render_kwargs:
            Extra keyword arguments forwarded to `VisualizationGraph.render`,
            e.g. `layout`, `max_allowed_nodes`, etc.
        """
        vg = from_neo4j(result)
        vg.color_nodes(field="caption")
        render_kwargs = render_kwargs or {}
        html_obj = vg.render(**render_kwargs)

        # `neo4j-viz` uses IPython.display.HTML under the hood.
        # Try to extract HTML from common attributes.
        html: str
        if hasattr(html_obj, "data"):
            html = html_obj.data
        elif hasattr(html_obj, "value"):
            html = html_obj.value
        else:
            # Fallback – IPython.HTML defines `_repr_html_`.
            html = str(getattr(html_obj, "_repr_html_", lambda: html_obj)())

        return cls(html=html, width=width, height=height)

    @classmethod
    def from_graph(
       cls,
       graph,
       *,
       width: str = "100%",
       height: str = "600px",
       render_kwargs: Optional[Dict[str, Any]] = None,
    ) -> "NvlWidget":
       """
       Create an NvlWidget from a `neo4j.Result` or `neo4j.graph.Graph`.

       Parameters
       ----------
       result:
             A Neo4j result object. For best results, use `Result.graph`
             as a transformer when executing the query.
       width, height:
             CSS-compatible width/height passed to the iframe (e.g. '100%', '800px').
       render_kwargs:
             Extra keyword arguments forwarded to `VisualizationGraph.render`,
             e.g. `layout`, `max_allowed_nodes`, etc.
       """
       vg = from_gds(G=graph)
       vg.color_nodes(field="caption")
       render_kwargs = render_kwargs or {}
       html_obj = vg.render(**render_kwargs)

       # `neo4j-viz` uses IPython.display.HTML under the hood.
       # Try to extract HTML from common attributes.
       html: str
       if hasattr(html_obj, "data"):
             html = html_obj.data
       elif hasattr(html_obj, "value"):
             html = html_obj.value
       else:
             # Fallback – IPython.HTML defines `_repr_html_`.
             html = str(getattr(html_obj, "_repr_html_", lambda: html_obj)())

       return cls(html=html, width=width, height=height)
