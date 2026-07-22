import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { Drawer, Table, Tabs, Tag } from "antd"
import type { ColumnsType, TableProps } from "antd/es/table"
import { useState } from "react"

import type {
  InventoryBalancePublic,
  InventoryLedgerEntryPublic,
  InventoryLedgerKind,
} from "@/client"
import { IamService } from "@/client"
import {
  readFinishedBalancesPage,
  readInventoryLedgerPage,
  readRawBalancesPage,
} from "@/features/inventory/api"
import {
  DEFAULT_PAGE_SIZE,
  PAGE_SIZE_OPTIONS,
  toOffset,
} from "@/features/inventory/pagination"

type BalanceKind = "raw" | "finished"

const balanceConfig: Record<
  BalanceKind,
  { label: string; ledgerKind: InventoryLedgerKind }
> = {
  finished: { label: "成品库存", ledgerKind: "FINISHED" },
  raw: { label: "来料库存", ledgerKind: "RAW" },
}

export function InventoryBalancesPage() {
  const permissionsQuery = useQuery({
    queryKey: ["iam", "permissions"],
    queryFn: IamService.readMyPermissions,
  })
  const canReadLedger =
    permissionsQuery.data?.permissions.includes("inventory.ledger.read") ??
    false
  const [activeKind, setActiveKind] = useState<BalanceKind>("raw")
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)
  const [ledgerPage, setLedgerPage] = useState(1)
  const [ledgerPageSize, setLedgerPageSize] = useState(DEFAULT_PAGE_SIZE)
  const [selectedBalance, setSelectedBalance] =
    useState<InventoryBalancePublic>()
  const balancesQuery = useQuery({
    queryFn: () =>
      activeKind === "raw"
        ? readRawBalancesPage({
            limit: pageSize,
            skip: toOffset(page, pageSize),
          })
        : readFinishedBalancesPage({
            limit: pageSize,
            skip: toOffset(page, pageSize),
          }),
    queryKey: ["inventory", "balances", activeKind, { page, pageSize }],
    placeholderData: keepPreviousData,
  })
  const ledgerQuery = useQuery({
    enabled: canReadLedger && Boolean(selectedBalance),
    queryFn: () =>
      readInventoryLedgerPage({
        colorCode: selectedBalance?.color_code ?? undefined,
        dyeLotNo: selectedBalance?.dye_lot_no ?? undefined,
        itemCode: selectedBalance?.item_code ?? undefined,
        itemName: selectedBalance?.item_name ?? "",
        ledgerKind: balanceConfig[activeKind].ledgerKind,
        limit: ledgerPageSize,
        processingUnitId: selectedBalance?.processing_unit_id ?? "",
        skip: toOffset(ledgerPage, ledgerPageSize),
        woolContent: selectedBalance?.wool_content ?? "",
      }),
    queryKey: [
      "inventory",
      "ledger",
      activeKind,
      selectedBalance,
      { page: ledgerPage, pageSize: ledgerPageSize },
    ],
    placeholderData: keepPreviousData,
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
  const handleTableChange: TableProps<InventoryBalancePublic>["onChange"] = (
    pagination,
  ) => {
    const nextPageSize = pagination.pageSize ?? pageSize
    setPageSize(nextPageSize)
    setPage(nextPageSize === pageSize ? (pagination.current ?? 1) : 1)
  }
  const handleLedgerTableChange: TableProps<InventoryLedgerEntryPublic>["onChange"] =
    (pagination) => {
      const nextPageSize = pagination.pageSize ?? ledgerPageSize
      setLedgerPageSize(nextPageSize)
      setLedgerPage(
        nextPageSize === ledgerPageSize ? (pagination.current ?? 1) : 1,
      )
    }

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
          setPage(1)
          setLedgerPage(1)
        }}
      />
      <Table
        columns={columns}
        dataSource={balancesQuery.data?.data ?? []}
        loading={balancesQuery.isFetching}
        locale={{ emptyText: "暂无库存余额" }}
        onRow={
          canReadLedger
            ? (balance) => ({
                onClick: () => {
                  setSelectedBalance(balance)
                  setLedgerPage(1)
                },
                style: { cursor: "pointer" },
              })
            : undefined
        }
        onChange={handleTableChange}
        pagination={{
          current: page,
          pageSize,
          pageSizeOptions: PAGE_SIZE_OPTIONS,
          responsive: true,
          showQuickJumper: true,
          showSizeChanger: true,
          showTotal: (total, [start, end]) => `${start}-${end} / ${total}`,
          total: balancesQuery.data?.count ?? 0,
        }}
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
      {canReadLedger ? (
        <Drawer
          onClose={() => {
            setSelectedBalance(undefined)
            setLedgerPage(1)
          }}
          open={Boolean(selectedBalance)}
          title={
            selectedBalance
              ? `${selectedBalance.item_name} 关联台账`
              : "关联台账"
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
            loading={ledgerQuery.isFetching}
            onChange={handleLedgerTableChange}
            pagination={{
              current: ledgerPage,
              pageSize: ledgerPageSize,
              pageSizeOptions: PAGE_SIZE_OPTIONS,
              responsive: true,
              showQuickJumper: true,
              showSizeChanger: true,
              showTotal: (total, [start, end]) => `${start}-${end} / ${total}`,
              total: ledgerQuery.data?.count ?? 0,
            }}
            rowKey="id"
            size="small"
          />
        </Drawer>
      ) : null}
    </div>
  )
}
