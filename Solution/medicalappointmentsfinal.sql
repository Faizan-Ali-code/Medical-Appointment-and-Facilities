-- phpMyAdmin SQL Dump
-- version 5.2.0
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Aug 01, 2023 at 10:39 PM
-- Server version: 10.4.24-MariaDB
-- PHP Version: 7.4.29

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `medicalappointmentsfinal`
--

-- --------------------------------------------------------

--
-- Table structure for table `appointments`
--

CREATE TABLE `appointments` (
  `id` int(20) NOT NULL,
  `user_id` int(20) DEFAULT NULL,
  `doctor_id` int(20) DEFAULT NULL,
  `hospital_id` int(20) DEFAULT NULL,
  `user_name` varchar(150) DEFAULT NULL,
  `user_age` varchar(50) DEFAULT NULL,
  `user_city` varchar(50) DEFAULT NULL,
  `doctor_slot` varchar(50) DEFAULT NULL,
  `date` date DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- Table structure for table `doctors`
--

CREATE TABLE `doctors` (
  `id` int(20) NOT NULL,
  `name` varchar(255) DEFAULT NULL,
  `hospital_id` int(20) DEFAULT NULL,
  `specialization` varchar(255) DEFAULT NULL,
  `fee` varchar(50) DEFAULT NULL,
  `slots` varchar(255) DEFAULT NULL,
  `description` varchar(255) DEFAULT NULL,
  `image` varchar(255) DEFAULT NULL,
  `days` varchar(50) DEFAULT ''
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `doctors`
--

INSERT INTO `doctors` (`id`, `name`, `hospital_id`, `specialization`, `fee`, `slots`, `description`, `image`) VALUES
(3, 'Sadaf', 3, 'MBBS ', '1600', '10:00 AM, 10:10 AM, 10:15 AM', 'MBBS from University of Health Sciences, Lahore, FCPS (Medicine) from College of Physicians and Surgeons, Pakistan and MRCP (UK) from Royal College Of Physicians and has 11 years of experience in this field.', 'wp10434441.png');

-- --------------------------------------------------------

--
-- Table structure for table `doctor_bookings`
--

CREATE TABLE `doctor_bookings` (
  `id` int(20) NOT NULL,
  `doctor_id` int(20) DEFAULT NULL,
  `user_id` int(20) DEFAULT NULL,
  `date` date DEFAULT NULL,
  `slot` varchar(100) DEFAULT NULL,
  `status` varchar(20) DEFAULT 'booked'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `doctor_bookings`
--

INSERT INTO `doctor_bookings` (`id`, `doctor_id`, `user_id`, `date`, `slot`) VALUES
(1, 3, 1, '2023-08-01', '10:00 AM');

-- --------------------------------------------------------

--
-- Table structure for table `facilities`
--

CREATE TABLE `facilities` (
  `id` int(20) NOT NULL,
  `hospital_id` int(20) DEFAULT NULL,
  `name` varchar(150) DEFAULT NULL,
  `description` varchar(255) DEFAULT NULL,
  `services` varchar(255) DEFAULT NULL,
  `fee` varchar(255) DEFAULT NULL,
  `contact` varchar(50) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `facilities`
--

INSERT INTO `facilities` (`id`, `hospital_id`, `name`, `description`, `services`, `fee`, `contact`) VALUES
(3, 3, 'Radiance Imaging Center', 'Radiance Imaging Center is a leading radiology facility equipped with advanced imaging technologies and a team of experienced radiologists. We provide high-quality diagnostic imaging services, enabling accurate visualization and interpretation of internal', 'X-rays, Ultrasound, CT Scan, MRI', '1500, 800, 2500, 3000', '03778899456');

-- --------------------------------------------------------

--
-- Table structure for table `facility_bookings`
--

CREATE TABLE `facility_bookings` (
  `id` int(20) NOT NULL,
  `facility_id` int(20) DEFAULT NULL,
  `user_id` int(20) DEFAULT NULL,
  `service` varchar(100) DEFAULT NULL,
  `image` varchar(255) DEFAULT NULL,
  `date` date DEFAULT NULL,
  `result` varchar(50) DEFAULT '-',
  `status` int(20) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `facility_bookings`
--

INSERT INTO `facility_bookings` (`id`, `facility_id`, `user_id`, `service`, `image`, `date`, `result`, `status`) VALUES
(1, 3, 1, 'as', 'chest-xray.jpg', '2023-08-01', '-', 0);

-- --------------------------------------------------------

--
-- Table structure for table `hospitals`
--

CREATE TABLE `hospitals` (
  `id` int(20) NOT NULL,
  `name` varchar(255) DEFAULT NULL,
  `city` varchar(50) DEFAULT NULL,
  `address` varchar(255) DEFAULT NULL,
  `phone` varchar(50) DEFAULT NULL,
  `description` text DEFAULT NULL,
  `image` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `hospitals`
--

INSERT INTO `hospitals` (`id`, `name`, `city`, `address`, `phone`, `description`, `image`) VALUES
(3, 'General Hospital', 'Lahore ', 'Ferozpur Road، near Chungi, Amar Sidhu Ismail Nagar, Lahore, Punjab 54000', '04299268801', 'Lahore General Hospital is a public sector teaching hospital located on Ferozepur Road in Lahore, Punjab, Pakistan. It is affiliated with Ameer-ud-Din Medical College, Lahore', 'lahore-general-hos-1.jpg');

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int(20) NOT NULL,
  `name` varchar(150) DEFAULT NULL,
  `email` varchar(150) DEFAULT NULL,
  `password` varchar(255) DEFAULT NULL,
  `phone` varchar(50) DEFAULT NULL,
  `city` varchar(50) DEFAULT NULL,
  `role` varchar(50) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `users`
--

-- Passwords below are plain text from the original project. The app hashes each one
-- automatically on first login, or run:  venv\Scripts\flask --app run hash-passwords
INSERT INTO `users` (`id`, `name`, `email`, `password`, `phone`, `city`, `role`) VALUES
(1, 'User', 'user@yahoo.com', 'user', '03108899456', 'Islamabad', 'user'),
(2, 'Salman', 'admin@yahoo.com', 'admin', '03998844444', 'Gujranwala', 'admin');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `appointments`
--
ALTER TABLE `appointments`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `doctors`
--
ALTER TABLE `doctors`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `doctor_bookings`
--
ALTER TABLE `doctor_bookings`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `facilities`
--
ALTER TABLE `facilities`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `facility_bookings`
--
ALTER TABLE `facility_bookings`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `hospitals`
--
ALTER TABLE `hospitals`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `appointments`
--
ALTER TABLE `appointments`
  MODIFY `id` int(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT for table `doctors`
--
ALTER TABLE `doctors`
  MODIFY `id` int(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `doctor_bookings`
--
ALTER TABLE `doctor_bookings`
  MODIFY `id` int(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `facilities`
--
ALTER TABLE `facilities`
  MODIFY `id` int(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT for table `facility_bookings`
--
ALTER TABLE `facility_bookings`
  MODIFY `id` int(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `hospitals`
--
ALTER TABLE `hospitals`
  MODIFY `id` int(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
