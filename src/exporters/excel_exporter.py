"""Excel 导出器（单 Sheet，10 列）。"""
import os
import time
from typing import List

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

import json

from src.models.sys_domain_change_usecase import SysDomainChangeUsecase
from src.utils.logger import get_logger
from src.utils.text_clean import sanitize_for_excel

log = get_logger(__name__)


class ExcelExporter:
    HEADERS = [
        "rdc_number", "方案",
        "特性域变更分析结果",
        "需求描述", "算法描述", "实现思路",
        "波及子系统",
        "波及组件",
        "波及模块",
        "波及的变更点",
    ]
    COLUMN_WIDTHS = [16, 50, 40, 40, 40, 40, 25, 60, 50, 40]

    HEADER_FILL = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    HEADER_FONT = Font(bold=True, color="FFFFFF")
    WRAP_ALIGN = Alignment(wrap_text=True, vertical="top")

    DEFAULT_DIR = "output"
    DEFAULT_FILENAME = "sys_domain_change_usecase.xlsx"

    def __init__(self, output_dir: str = DEFAULT_DIR):
        self.output_dir = output_dir

    def export(self, records: List[SysDomainChangeUsecase]) -> str:
        os.makedirs(self.output_dir, exist_ok=True)
        path = os.path.join(self.output_dir, self.DEFAULT_FILENAME)

        wb = Workbook()
        wb.remove(wb.active)
        ws = wb.create_sheet("方案汇总")
        self._write_header(ws)

        total = len(records)
        log_step = max(1, total // 10)
        start = time.time()
        log.info("Excel 导出开始：{} 行", total)
        done = 0

        for r in records:
            row = [
                r.rdc_number, r.title,
                r.feature_change_analysis,
                r.description, r.algorithm, r.implementation,
                r.sub_systems,
                r.affected_components,
                r.affected_modules,
                r.change_points,
            ]
            self._append_row(ws, row)
            done += 1
            if done % log_step == 0 or done == total:
                self._log_progress(done, total, start)

        for i, w in enumerate(self.COLUMN_WIDTHS, 1):
            ws.column_dimensions[get_column_letter(i)].width = w
        ws.freeze_panes = "A2"

        wb.save(path)
        log.info("Excel 已写入: {} | {}s", path, int(time.time() - start))
        return path

    def _write_header(self, ws):
        for col_idx, h in enumerate(self.HEADERS, 1):
            c = ws.cell(row=1, column=col_idx, value=h)
            c.fill = self.HEADER_FILL
            c.font = self.HEADER_FONT
            c.alignment = Alignment(horizontal="center", vertical="center")

    @staticmethod
    def _format_json(s):
        """把紧凑 JSON 格式化（indent=2），让 Excel 单元格显示更可读。

        不是 JSON 则原样返回。
        """
        if not s:
            return ""
        try:
            obj = json.loads(s)
            return json.dumps(obj, indent=2, ensure_ascii=False)
        except Exception:
            return s

    def _append_row(self, ws, row):
        # JSON 列缩进格式化（看起来"更好看"）
        formatted = []
        for v in row:
            if isinstance(v, str) and v.startswith(("[", "{")):
                formatted.append(self._format_json(v))
            else:
                formatted.append(sanitize_for_excel(v))
        ws.append(formatted)
        for cell in ws[ws.max_row]:
            cell.alignment = self.WRAP_ALIGN

    def _log_progress(self, done, total, start):
        elapsed = time.time() - start
        rate = done / elapsed if elapsed > 0 else 0
        eta = (total - done) / rate if rate > 0 else 0
        log.info(
            "Excel [{:<6}] {:>6}/{:<6} ({:>4.0%}) | 速率 {:>5.0f} 行/s | 剩余 {:>4.1f}s",
            "方案汇总", done, total, done / total, rate, eta,
        )
