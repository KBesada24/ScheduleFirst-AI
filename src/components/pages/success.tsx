import { CheckCircle } from 'lucide-react'
import { motion } from 'framer-motion'
import { NavigationButton } from '@/components/ui/navigation-button'

export default function Success() {
    return (
        <div className="min-h-screen bg-gradient-to-br from-green-50 to-green-100 flex items-center justify-center p-4">
            <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="bg-white rounded-lg shadow-xl p-8 max-w-md w-full text-center"
            >
                <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
                >
                    <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
                </motion.div>
                <motion.h1 
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.4 }}
                    className="text-3xl font-bold text-gray-800 mb-4"
                >
                    Welcome to ScheduleFirst AI!
                </motion.h1>
                <motion.p 
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.6 }}
                    className="text-gray-600 mb-6"
                >
                    Your account has been created successfully. Let's get started building your optimal schedule!
                </motion.p>
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.8 }}
                >
                    <NavigationButton 
                        to="/dashboard"
                        className="bg-green-500 text-white px-6 py-3 rounded-lg font-semibold hover:bg-green-600"
                        requiresAuth
                    >
                        Go to Dashboard
                    </NavigationButton>
                </motion.div>
            </motion.div>
        </div>
    )
}