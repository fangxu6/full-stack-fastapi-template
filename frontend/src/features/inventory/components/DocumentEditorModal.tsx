import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  App,
  Button,
  DatePicker,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
} from "antd"
import dayjs from "dayjs"
import { Minus, Plus } from "lucide-react"

import {
  type InventoryDocumentCreate,
  type InventoryDocumentPublic,
  type InventoryLineCreate,
  InventoryService,
} from "@/client"

type DocumentFormValues = {
  business_date: ReturnType<typeof dayjs>
  document_number?: string
  lines: Partial<InventoryLineCreate>[]
  processing_unit_id?: string
  receiving_unit_id?: string
  remarks?: string
}

type DocumentEditorModalProps = {
  document?: InventoryDocumentPublic
  documentType: InventoryDocumentCreate["document_type"]
  onClose: () => void
  open: boolean
}

const documentLabels = {
  FINISHED_RECEIPT: "成品入库",
  FINISHED_SHIPMENT: "成品出货",
  RAW_RECEIPT: "坯布入库",
  RAW_RETURN: "坯布退走",
} as const

function isFinishedShipment(
  documentType: InventoryDocumentCreate["document_type"],
) {
  return documentType === "FINISHED_SHIPMENT"
}

export function DocumentEditorModal({
  document,
  documentType,
  onClose,
  open,
}: DocumentEditorModalProps) {
  const [form] = Form.useForm<DocumentFormValues>()
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const isShipment = isFinishedShipment(documentType)
  const processingUnitsQuery = useQuery({
    queryFn: () => InventoryService.readProcessingUnits(),
    queryKey: ["inventory-processing-units"],
  })
  const receivingUnitsQuery = useQuery({
    enabled: isShipment,
    queryFn: () => InventoryService.readReceivingUnits(),
    queryKey: ["inventory-receiving-units"],
  })
  const mutation = useMutation({
    mutationFn: (values: InventoryDocumentCreate) =>
      document
        ? InventoryService.updateInventoryDocument({
            documentId: document.id,
            requestBody: values,
          })
        : InventoryService.createInventoryDocument({ requestBody: values }),
    onError: () => {
      message.error("保存失败，请检查库存和单据字段。")
    },
    onSuccess: () => {
      message.success(document ? "单据已更新" : "单据已保存")
      void queryClient.invalidateQueries({ queryKey: ["inventory"] })
      onClose()
    },
  })

  const initialValues: DocumentFormValues = {
    business_date: document ? dayjs(document.business_date) : dayjs(),
    document_number: document?.document_number ?? "",
    lines: document?.lines.map((line) => ({
      color_code: line.color_code ?? undefined,
      dye_lot_no: line.dye_lot_no ?? undefined,
      item_code: line.item_code ?? undefined,
      item_name: line.item_name,
      quantity_meters: line.quantity_meters
        ? Number(line.quantity_meters)
        : undefined,
      quantity_rolls: line.quantity_rolls,
      wool_content: line.wool_content,
    })) ?? [{}],
    processing_unit_id: document?.processing_unit_id,
    receiving_unit_id: document?.receiving_unit_id ?? undefined,
    remarks: document?.remarks ?? undefined,
  }

  const submit = (values: DocumentFormValues) => {
    const payload: InventoryDocumentCreate = {
      business_date: values.business_date.format("YYYY-MM-DD"),
      document_type: documentType,
      document_number: values.document_number ?? "",
      lines: values.lines.map((line) => line as InventoryLineCreate),
      processing_unit_id: values.processing_unit_id ?? "",
      receiving_unit_id: values.receiving_unit_id ?? null,
      remarks: values.remarks ?? null,
    }
    mutation.mutate(payload)
  }

  return (
    <Modal
      destroyOnHidden
      footer={null}
      onCancel={onClose}
      open={open}
      title={`${document ? "编辑" : "新建"}${documentLabels[documentType]}`}
      width={960}
    >
      <Form
        form={form}
        initialValues={initialValues}
        layout="vertical"
        onFinish={submit}
      >
        <div className="grid gap-x-4 md:grid-cols-2">
          <Form.Item
            label="业务日期"
            name="business_date"
            rules={[{ required: true }]}
          >
            <DatePicker className="w-full" />
          </Form.Item>
          <Form.Item
            label="单号"
            name="document_number"
            rules={[{ required: true }]}
          >
            <Input maxLength={64} />
          </Form.Item>
          <Form.Item
            label="加工单位"
            name="processing_unit_id"
            rules={[{ required: true }]}
          >
            <Select
              loading={processingUnitsQuery.isLoading}
              options={(processingUnitsQuery.data?.data ?? [])
                .filter(
                  (unit) =>
                    unit.is_active || unit.id === document?.processing_unit_id,
                )
                .map((unit) => ({ label: unit.name, value: unit.id }))}
              showSearch
            />
          </Form.Item>
          {isShipment ? (
            <Form.Item
              label="收货单位"
              name="receiving_unit_id"
              rules={[{ required: true }]}
            >
              <Select
                loading={receivingUnitsQuery.isLoading}
                options={(receivingUnitsQuery.data?.data ?? [])
                  .filter(
                    (unit) =>
                      unit.is_active || unit.id === document?.receiving_unit_id,
                  )
                  .map((unit) => ({ label: unit.name, value: unit.id }))}
                showSearch
              />
            </Form.Item>
          ) : null}
        </div>

        <Form.List name="lines">
          {(fields, { add, remove }) => (
            <div className="space-y-3">
              {fields.map((field, index) => (
                <div
                  className="grid gap-x-3 rounded-md border p-3 md:grid-cols-6"
                  key={field.key}
                >
                  <Form.Item
                    className="md:col-span-2"
                    label={index === 0 ? "品名" : undefined}
                    name={[field.name, "item_name"]}
                    rules={[{ required: true }]}
                  >
                    <Input />
                  </Form.Item>
                  {!isShipment ? (
                    <Form.Item
                      label={index === 0 ? "品号" : undefined}
                      name={[field.name, "item_code"]}
                      rules={[{ required: true }]}
                    >
                      <Input />
                    </Form.Item>
                  ) : null}
                  <Form.Item
                    label={index === 0 ? "含毛量" : undefined}
                    name={[field.name, "wool_content"]}
                    rules={[{ required: true }]}
                  >
                    <Input />
                  </Form.Item>
                  {isShipment ? (
                    <>
                      <Form.Item
                        label={index === 0 ? "颜色/色号" : undefined}
                        name={[field.name, "color_code"]}
                        rules={[{ required: true }]}
                      >
                        <Input />
                      </Form.Item>
                      <Form.Item
                        label={index === 0 ? "缸号" : undefined}
                        name={[field.name, "dye_lot_no"]}
                        rules={[{ required: true }]}
                      >
                        <Input />
                      </Form.Item>
                    </>
                  ) : null}
                  <Form.Item
                    label={index === 0 ? "匹数" : undefined}
                    name={[field.name, "quantity_rolls"]}
                    rules={[{ required: true, message: "请输入正整数" }]}
                  >
                    <InputNumber className="w-full" min={1} precision={0} />
                  </Form.Item>
                  {isShipment ? (
                    <Form.Item
                      label={index === 0 ? "米数" : undefined}
                      name={[field.name, "quantity_meters"]}
                      rules={[{ required: true, message: "请输入正数" }]}
                    >
                      <InputNumber
                        className="w-full"
                        min={0.001}
                        precision={3}
                      />
                    </Form.Item>
                  ) : null}
                  <Button
                    aria-label="删除明细"
                    className="self-end"
                    disabled={fields.length === 1}
                    icon={<Minus size={16} />}
                    onClick={() => remove(field.name)}
                    type="text"
                  />
                </div>
              ))}
              <Button
                icon={<Plus size={16} />}
                onClick={() => add({})}
                type="dashed"
              >
                添加明细
              </Button>
            </div>
          )}
        </Form.List>
        <Form.Item label="备注" name="remarks" className="mt-4">
          <Input.TextArea autoSize={{ minRows: 2, maxRows: 4 }} />
        </Form.Item>
        <div className="flex justify-end gap-2">
          <Button onClick={onClose}>取消</Button>
          <Button htmlType="submit" loading={mutation.isPending} type="primary">
            保存
          </Button>
        </div>
      </Form>
    </Modal>
  )
}
