import { getReceiptUrl } from "../api";

export default function OrderTable({ orders, onEdit, onDelete }) {
  if (orders.length === 0) {
    return <p className="empty-state">No orders found.</p>;
  }

  return (
    <table className="order-table">
      <thead>
        <tr>
          <th>Order ID</th>
          <th>Product ID</th>
          <th>Qty</th>
          <th>Price</th>
          <th>Order Date</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {orders.map((order) => (
          <tr key={order.OrderID}>
            <td>{order.OrderID}</td>
            <td>{order.ProductID}</td>
            <td>{order.Qty}</td>
            <td>{order.Price.toFixed(2)}</td>
            <td>{order.OrderDate}</td>
            <td className="row-actions">
              <button onClick={() => onEdit(order)}>Edit</button>
              <button onClick={() => onDelete(order.OrderID)}>Delete</button>
              <a
                className="receipt-link"
                href={getReceiptUrl(order.OrderID)}
                target="_blank"
                rel="noreferrer"
              >
                Receipt
              </a>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
