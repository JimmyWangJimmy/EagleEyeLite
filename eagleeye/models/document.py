"""
Document data models for parsed PDF content.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class TableData(BaseModel):
    """Represents an extracted table from PDF."""

    page_number: int
    table_index: int
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    raw_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for financial data extraction."""
        result = {}
        for row in self.rows:
            if len(row) >= 2:
                key = row[0].strip()
                value = row[-1].strip()
                if key:
                    result[key] = value
        return result


class FinancialData(BaseModel):
    """Extracted financial data from document."""

    # 资产负债表 (Balance Sheet)
    货币资金: Optional[float] = None
    应收账款: Optional[float] = None
    应收账款_期初: Optional[float] = None
    应收账款_期末: Optional[float] = None
    应收账款_3年以上占比: Optional[float] = None
    其他应收款: Optional[float] = None
    预付账款: Optional[float] = None
    存货: Optional[float] = None
    存货_期初余额: Optional[float] = None
    存货_期末余额: Optional[float] = None
    存货_土地开发成本: Optional[float] = None
    存货周转率: Optional[float] = None
    在建工程: Optional[float] = None
    在建工程_本期增加额: Optional[float] = None
    在建工程_概算总投资: Optional[float] = None
    在建工程_累计已投入金额: Optional[float] = None
    固定资产: Optional[float] = None
    固定资产_本期减少额: Optional[float] = None
    无形资产: Optional[float] = None
    无形资产_本期增加额: Optional[float] = None
    无形资产_特许经营权: Optional[float] = None
    资产总额: Optional[float] = None
    受限资产: Optional[float] = None
    公益性资产: Optional[float] = None

    短期借款: Optional[float] = None
    短期借款_期初: Optional[float] = None
    短期借款_增加额: Optional[float] = None
    长期借款: Optional[float] = None
    长期借款_期初: Optional[float] = None
    应付债券: Optional[float] = None
    一年内到期的非流动负债: Optional[float] = None
    一年内到期非流动负债_期初: Optional[float] = None
    其他应付款: Optional[float] = None
    其他应付款_关联方_增加额: Optional[float] = None
    递延收益_期初: Optional[float] = None
    递延收益_期末: Optional[float] = None
    有息债务_期末: Optional[float] = None
    资本公积_本期减少额: Optional[float] = None
    净资产: Optional[float] = None
    资产负债率: Optional[float] = None

    # 利润表 (Income Statement)
    营业收入: Optional[float] = None
    营业收入_代建业务: Optional[float] = None
    营业收入_贸易板块占比: Optional[float] = None
    营业收入_贸易业务占比: Optional[float] = None
    营业收入_贸易业务_毛利率: Optional[float] = None
    营业成本: Optional[float] = None
    销售毛利率_贸易业务: Optional[float] = None
    财务费用_利息支出: Optional[float] = None
    财务费用_非标融资平均利率: Optional[float] = None
    研发费用: Optional[float] = None
    营业外收入_政府补助: Optional[float] = None
    其他收益_政府补助: Optional[float] = None
    利润总额: Optional[float] = None
    净利润: Optional[float] = None
    净资产收益率_ROE: Optional[float] = None
    息税前利润_EBIT: Optional[float] = None
    平均资产总额: Optional[float] = None

    # 现金流量表 (Cash Flow Statement)
    经营活动现金流量净额: Optional[float] = None
    经营活动现金流入: Optional[float] = None
    销售商品提供劳务收到的现金: Optional[float] = None
    收到其他与经营活动有关的现金_政府补助: Optional[float] = None
    购买商品接受劳务支付的现金: Optional[float] = None

    投资活动现金流出: Optional[float] = None
    购建固定资产无形资产和其他长期资产支付的现金: Optional[float] = None
    购建固定资产无形资产支付的现金: Optional[float] = None
    购建资产_支付给职工的现金: Optional[float] = None

    筹资活动现金流入: Optional[float] = None
    取得借款收到的现金: Optional[float] = None
    筹资活动_偿还债务支付的现金: Optional[float] = None
    分配股利利润或偿付利息支付的现金: Optional[float] = None
    分配股利: Optional[float] = None

    # 补充资料 (Supplementary)
    补充资料_存货的减少: Optional[float] = None
    补充资料_经营性应收项目的减少: Optional[float] = None

    # 资本化利息
    在建工程_资本化利息: Optional[float] = None

    # 历史数据
    最近3年_经营活动现金流量净额: list[float] = Field(default_factory=list)

    # 行业数据
    行业上年度平均资产负债率: Optional[float] = None
    行业类型: Optional[str] = None

    # 融资相关
    非标融资余额: Optional[float] = None
    有息债务总额: Optional[float] = None
    上年度_非标融资占比: Optional[float] = None
    银行授信_未使用额度: Optional[float] = None
    对外担保余额_合计: Optional[float] = None
    非主业投资金额: Optional[float] = None
    综合融资成本_年化: Optional[float] = None
    融资类型: Optional[str] = None

    # 债券相关
    债券发行日_前后30天内_其他应收款_新增额: Optional[float] = None
    债券发行额: Optional[float] = None
    其他应收款_交易对象: list[str] = Field(default_factory=list)
    募集资金总额: Optional[float] = None
    募集说明书_承诺偿还金额: Optional[float] = None

    # 隐性债务
    隐性债务监测表_余额_减少额: Optional[float] = None

    # 诉讼
    单笔涉案金额: Optional[float] = None
    上年度经审计净资产: Optional[float] = None
    项目类型: Optional[str] = None

    # 行政处罚
    收到行政处罚决定书: Optional[bool] = None
    收到行政监管惩戒措施: Optional[bool] = None

    # 资产处置
    资产处置收益: Optional[float] = None
    无偿划转批复文件: Optional[str] = None

    def get(self, key: str, default: Any = None) -> Any:
        """Get attribute value with default."""
        return getattr(self, key, default)

    def to_eval_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logic evaluation."""
        result = {}
        for field_name, field_value in self:
            if field_value is not None:
                # Replace Chinese field names with underscored versions
                key = field_name.replace("_", "_")
                result[key] = field_value
        return result


class Document(BaseModel):
    """Represents a parsed PDF document."""

    file_path: str
    file_name: str
    total_pages: int
    parse_method: str = Field(description="pdfplumber or ocr")
    parsed_at: datetime = Field(default_factory=datetime.now)

    raw_text: str = ""
    tables: list[TableData] = Field(default_factory=list)
    financial_data: FinancialData = Field(default_factory=FinancialData)

    @property
    def text_density(self) -> float:
        """Calculate average text density per page."""
        if self.total_pages == 0:
            return 0
        return len(self.raw_text) / self.total_pages

    def extract_keywords(self) -> list[str]:
        """Extract potential keywords from document text."""
        # Common financial terms
        keywords = []
        terms = [
            "政府补助", "营业外收入", "递延收益", "在建工程", "存货",
            "应收账款", "其他应收款", "短期借款", "长期借款", "有息债务",
            "经营活动现金流", "投资活动", "筹资活动", "贸易收入", "毛利率"
        ]
        for term in terms:
            if term in self.raw_text:
                keywords.append(term)
        return keywords
