"use client"

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface SpendingChartProps {
  data: Array<{ date: string; amount: number }>
}

export default function SpendingChart({ data }: SpendingChartProps) {
  return (
    <Card className="col-span-4">
      <CardHeader>
        <CardTitle>Spending Over Time</CardTitle>
      </CardHeader>
      <CardContent className="pl-2">
        <div className="h-[200px] w-full">
            <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis 
                    dataKey="date" 
                    stroke="#888888" 
                    fontSize={12} 
                    tickLine={false} 
                    axisLine={false} 
                    tickFormatter={(value) => {
                        const date = new Date(value);
                        return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
                    }}
                />
                <YAxis
                    stroke="#888888"
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(value) => `€${value}`}
                />
                <Tooltip 
                    formatter={(value: any) => [`€${value}`, "Amount"]}
                    labelFormatter={(label) => new Date(label).toLocaleDateString()}
                    filterNull={false}
                />
                <Line
                    type="monotone"
                    dataKey="amount"
                    stroke="#2563eb" // primary blue
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4 }}
                />
            </LineChart>
            </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
