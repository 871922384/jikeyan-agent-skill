"""本机公开数据源检索：参考文献核验与选题撞题检索。

只使用标准库（urllib）访问 Crossref、NCBI PubMed、ClinicalTrials.gov
公开接口；不访问极科研服务端，不发送患者信息。
"""

from __future__ import annotations

from jikeyan_mcp.local_search import pubmed, references, topic_collision

__all__ = ["pubmed", "references", "topic_collision"]
