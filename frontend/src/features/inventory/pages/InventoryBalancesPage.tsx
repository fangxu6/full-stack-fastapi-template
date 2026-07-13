import { useQuery } from "@tanstack/react-query"
import { Drawer, Table, Tabs, Tag } from "antd"
import type { ColumnsType } from "antd/es/table"
import { useState } from "react"

import {
  type InventoryBalancePublic,
  type InventoryLedgerKind,
  InventoryService,
} from "@/client"

type BalanceKind = "raw" | "finished"

const balanceConfig: Record<
  BalanceKind,
  { label: string; ledgerKind: InventoryLedgerKind }
> = {
  finished: { label: "成品库存", ledgerKind: "FINISHED" },
  raw: { label: "来料库存", ledgerKind: "RAW" },
}

export function InventoryBalancesPage() {
  const [activeKind, setActiveKind] = useState<BalanceKind>("raw")
  const [selectedBalance, setSelectedBalance] =
    useState<InventoryBalancePublic>()
  const balancesQuery = useQuery({
    queryFn: () =>
      activeKind === "raw"
        ? InventoryService.readRawBalances()
        : InventoryService.readFinishedBalances(),
    queryKey: ["inventory", "balances", activeKind],
  })
  const ledgerQuery = useQuery({
    enabled: Boolean(selectedBalance),
    queryFn: () =>
      InventoryService.readInventoryLedger({
        colorCode: selectedBalance?.color_code ?? undefined,
        dyeLotNo: selectedBalance?.dye_lot_no ?? undefined,
        itemCode: selectedBalance?.item_code ?? undefined,
        itemName: selectedBalance?.item_name ?? "",
        ledgerKind: balanceConfig[activeKind].ledgerKind,
        processingUnitId: selectedBalance?.processing_unit_id ?? "",
        woolContent: selectedBalance?.wool_content ?? "",
      }),
    queryKey: ["inventory", "ledger", activeKind, selectedBalance],
  })
  const columns: ColumnsType<InventoryBalancePublic> = [
    { dataIndex: "item_name", title: "品名" },
    { dataIndex: "item_code", title: "品号" },
    { dataIndex: "wool_content", title: "含毛量" },
    { dataIndex: "color_code", title: "颜色/色号" },
    { dataIndex: "dye_lot_no", title: "缸号" },
    { dataIndex: "rolls_balance", title: "可用匹数", width: 110 },
    {
      dataIndex: "meters_balance",
      render: (value: string) => (activeKind === "finished" ? value : "-"),
      title: "可用米数",
      width: 110,
    },
  ]

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h1 className="text-2xl font-semibold">库存余额</h1>
        <p className="text-sm text-muted-foreground">
          余额由所有生效台账明细聚合得出，不可直接编辑。
        </p>
      </div>
      <Tabs
        activeKey={activeKind}
        items={Object.entries(balanceConfig).map(([key, config]) => ({
          key,
          label: config.label,
        }))}
        onChange={(key) => {
          setSelectedBalance(undefined)
          setActiveKind(key as BalanceKind)
        }}
      />
      <Table
        columns={columns}
        dataSource={balancesQuery.data?.data ?? []}
        loading={balancesQuery.isLoading}
        locale={{ emptyText: "暂无库存余额" }}
        onRow={(balance) => ({
          onClick: () => setSelectedBalance(balance),
          style: { cursor: "pointer" },
        })}
        pagination={{ pageSize: 20, showSizeChanger: false }}
        rowKey={(balance) =>
          [
            balance.processing_unit_id,
            balance.item_name,
            balance.item_code,
            balance.wool_content,
            balance.color_code,
            balance.dye_lot_no,
          ].join("-")
        }
        scroll={{ x: 760 }}
      />
      <Drawer
        onClose={() => setSelectedBalance(undefined)}
        open={Boolean(selectedBalance)}
        title={
          selectedBalance ? `${selectedBalance.item_name} 关联台账` : "关联台账"
        }
        width={760}
      >
        <Table
          columns={[
            { dataIndex: "business_date", title: "日期", width: 110 },
            { dataIndex: "movement_type", title: "变动类型" },
            { dataIndex: "rolls_delta", title: "匹数变动" },
            { dataIndex: "meters_delta", title: "米数变动" },
            {
              dataIndex: "reason",
              render: (value: string | null) => value ?? <Tag>业务单据</Tag>,
              title: "来源",
            },
          ]}
          dataSource={ledgerQuery.data?.data ?? []}
          loading={ledgerQuery.isLoading}
          pagination={false}
          rowKey="id"
          size="small"
        />
      </Drawer>
    </div>
  )
}
